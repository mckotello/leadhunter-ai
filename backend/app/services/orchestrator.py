import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.ai_analyst import AIAnalystAgent
from app.agents.offer_agent import OfferAgent
from app.agents.parser_agent import ParserAgent
from app.agents.scoring_agent import ScoringAgent
from app.agents.search_agent import SearchAgent
from app.integrations.search.base import SearchHit
from app.models.entities import (
    Company,
    GeneratedOffer,
    Lead,
    LeadStatus,
    LeadTemperature,
    SearchTask,
    SearchTaskStatus,
    Source,
)
from app.schemas.domain import NeedType, SearchCreate, extract_domain, normalize_company_name

logger = logging.getLogger(__name__)


class CompanyRepository:
    async def upsert_from_hit(self, session: AsyncSession, hit: SearchHit, niche: str, region: str) -> Company:
        domain = extract_domain(hit.website)
        normalized = normalize_company_name(hit.name)
        if domain:
            stmt = select(Company).where((Company.domain == domain) | (Company.normalized_name == normalized))
        else:
            stmt = select(Company).where(Company.normalized_name == normalized)

        result = await session.execute(stmt)
        company = result.scalar_one_or_none()
        if company:
            if not company.website and hit.website:
                company.website = hit.website
            return company

        company = Company(
            name=hit.name[:512],
            website=hit.website,
            industry=niche,
            region=region,
            description=hit.snippet,
            normalized_name=normalized,
            domain=domain,
        )
        session.add(company)
        await session.flush()

        session.add(
            Source(
                company_id=company.id,
                source_url=hit.source_url,
                source_type=hit.source_type,
                extracted_data={"snippet": hit.snippet},
            )
        )
        return company


class LeadService:
    async def get_lead_detail(self, session: AsyncSession, lead_id: int) -> Lead | None:
        stmt = (
            select(Lead)
            .where(Lead.id == lead_id)
            .options(
                selectinload(Lead.company).selectinload(Company.sources),
                selectinload(Lead.notes),
                selectinload(Lead.offers),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_leads(
        self,
        session: AsyncSession,
        status: str | None = None,
        min_score: int | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Lead]:
        stmt = select(Lead).join(Company).options(selectinload(Lead.company))
        if status:
            stmt = stmt.where(Lead.status == LeadStatus(status))
        if min_score is not None:
            stmt = stmt.where(Lead.score >= min_score)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(Company.name.ilike(like) | Company.industry.ilike(like))
        stmt = stmt.order_by(Lead.score.desc().nullslast(), Lead.id.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())


class Orchestrator:
    def __init__(self) -> None:
        self.search_agent = SearchAgent()
        self.parser_agent = ParserAgent()
        self.ai_analyst = AIAnalystAgent()
        self.scoring_agent = ScoringAgent()
        self.offer_agent = OfferAgent()
        self.company_repo = CompanyRepository()

    async def create_search_task(self, session: AsyncSession, payload: SearchCreate) -> SearchTask:
        query = (
            f"Найти {payload.limit} компаний: {payload.niche}, {payload.region}, "
            f"ключевые слова: {payload.keywords}, потребность: {payload.need_type.value}"
        )
        task = SearchTask(
            query=query,
            filters=payload.model_dump(mode="json"),
            status=SearchTaskStatus.PENDING,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task

    async def run_search_pipeline(self, session: AsyncSession, task_id: int) -> None:
        task = await session.get(SearchTask, task_id)
        if not task:
            raise ValueError(f"Search task {task_id} not found")

        task.status = SearchTaskStatus.RUNNING
        await session.commit()

        payload = SearchCreate.model_validate(task.filters or {})
        try:
            hits = await self.search_agent.run(payload)
            task.total_found = len(hits)
            processed = 0
            for hit in hits:
                company = await self.company_repo.upsert_from_hit(
                    session, hit, niche=payload.niche, region=payload.region
                )
                lead = await self._ensure_lead(session, company.id)
                if hit.website:
                    await self._parse_and_analyze(session, lead, company, payload)
                processed += 1
                task.total_processed = processed
                await session.commit()

            task.status = SearchTaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            logger.exception("Search pipeline failed for task %s", task_id)
            task.status = SearchTaskStatus.FAILED
            task.error_message = str(exc)
            task.completed_at = datetime.now(timezone.utc)
        await session.commit()

    async def reanalyze_lead(self, session: AsyncSession, lead_id: int) -> Lead:
        lead = await session.get(Lead, lead_id, options=(selectinload(Lead.company),))
        if not lead or not lead.company:
            raise ValueError("Lead not found")
        company = lead.company
        if not company.website:
            raise ValueError("У компании нет сайта для анализа")
        payload = SearchCreate(
            niche=company.industry or "бизнес",
            region=company.region or "Россия",
            keywords="",
            need_type=NeedType.OTHER,
            limit=1,
        )
        await self._parse_and_analyze(session, lead, company, payload)
        await session.commit()
        await session.refresh(lead)
        return lead

    async def generate_offer(self, session: AsyncSession, lead_id: int) -> GeneratedOffer:
        lead = await session.get(Lead, lead_id, options=(selectinload(Lead.company),))
        if not lead or not lead.ai_analysis:
            raise ValueError("Сначала выполните AI-анализ")
        analysis = lead.ai_analysis
        from app.schemas.domain import AIAnalysisResult

        parsed_analysis = AIAnalysisResult.model_validate(analysis)
        draft = self.offer_agent.generate(lead.company.name, parsed_analysis)
        content = self.offer_agent.format_offer_text(draft)
        offer = GeneratedOffer(lead_id=lead.id, content=content)
        session.add(offer)
        await session.commit()
        await session.refresh(offer)
        return offer

    async def _ensure_lead(self, session: AsyncSession, company_id: int) -> Lead:
        result = await session.execute(select(Lead).where(Lead.company_id == company_id))
        lead = result.scalar_one_or_none()
        if lead:
            return lead
        lead = Lead(company_id=company_id, status=LeadStatus.NEW)
        session.add(lead)
        await session.flush()
        return lead

    async def _parse_and_analyze(
        self, session: AsyncSession, lead: Lead, company: Company, payload: SearchCreate
    ) -> None:
        parsed = await self.parser_agent.parse(company.website or "", company.name)
        session.add(
            Source(
                company_id=company.id,
                source_url=parsed.source_url or company.website or "",
                source_type="website_parser",
                extracted_data={
                    "signals": parsed.signals.__dict__,
                    "products_services": parsed.products_services,
                    "contact_pages": parsed.contact_pages,
                },
            )
        )
        if parsed.description and not company.description:
            company.description = parsed.description
        if parsed.phone:
            company.phone = parsed.phone
        if parsed.email:
            company.email = parsed.email
        if parsed.social_links:
            company.social_links = parsed.social_links

        analysis = self.ai_analyst.analyze(
            company.name, parsed, niche=payload.niche, need_type=payload.need_type.value
        )
        scoring = self.scoring_agent.score(
            niche=payload.niche,
            industry=company.industry,
            analysis=analysis,
            has_phone=bool(company.phone),
            has_email=bool(company.email),
            parsed=parsed,
        )

        lead.detected_needs = analysis.assumed_needs
        lead.recommended_services = [analysis.recommended_service]
        lead.ai_analysis = analysis.model_dump(mode="json")
        lead.confidence = analysis.confidence
        lead.score = scoring.score
        lead.score_explanation = scoring.explanation
        lead.temperature = LeadTemperature(scoring.temperature)
        lead.status = LeadStatus.ANALYZED


class DashboardService:
    async def stats(self, session: AsyncSession) -> dict:
        companies = await session.scalar(select(func.count()).select_from(Company)) or 0
        analyzed = await session.scalar(
            select(func.count()).select_from(Lead).where(Lead.status != LeadStatus.NEW)
        ) or 0
        hot = await session.scalar(
            select(func.count()).select_from(Lead).where(Lead.temperature == LeadTemperature.HOT)
        ) or 0
        warm = await session.scalar(
            select(func.count()).select_from(Lead).where(Lead.temperature == LeadTemperature.WARM)
        ) or 0
        tasks = await session.scalar(select(func.count()).select_from(SearchTask)) or 0

        dist_rows = await session.execute(
            select(Lead.temperature, func.count())
            .group_by(Lead.temperature)
        )
        distribution = {str(k.value if k else "none"): v for k, v in dist_rows.all()}

        recent_result = await session.execute(select(Company).order_by(Company.created_at.desc()).limit(8))
        recent = list(recent_result.scalars().all())
        return {
            "total_companies": companies,
            "analyzed_leads": analyzed,
            "hot_leads": hot,
            "warm_leads": warm,
            "search_tasks": tasks,
            "temperature_distribution": distribution,
            "recent_companies": recent,
        }
