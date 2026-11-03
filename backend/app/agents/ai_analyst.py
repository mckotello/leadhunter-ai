import logging

from app.agents.parser_agent import ParsedCompany
from app.integrations.llm.client import LLMClient
from app.schemas.domain import AIAnalysisResult, FactReference

logger = logging.getLogger(__name__)

SYSTEM = """Ты B2B-аналитик IT-студии. Анализируй только факты из входных данных.
Не выдавай предположения за подтверждённые факты. Если данных недостаточно — понижай confidence.
Ответ строго в JSON с полями:
business_summary, identified_issues, assumed_needs, recommended_service, rationale, confidence, evidence
evidence — массив объектов {fact, source_url}."""


class AIAnalystAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def analyze(self, company_name: str, parsed: ParsedCompany, niche: str, need_type: str) -> AIAnalysisResult:
        user = self._build_prompt(company_name, parsed, niche, need_type)
        try:
            return self.llm.complete_json(SYSTEM, user, AIAnalysisResult)
        except Exception as exc:
            logger.exception("AI analysis failed, using heuristic fallback: %s", exc)
            return self._fallback(company_name, parsed)

    def _build_prompt(self, company_name: str, parsed: ParsedCompany, niche: str, need_type: str) -> str:
        signals = parsed.signals
        return f"""
Компания: {company_name}
Ниша задачи: {niche}
Тип потребности: {need_type}
URL: {parsed.source_url}
Описание: {parsed.description}
Телефон: {parsed.phone}
Email: {parsed.email}
Сигналы сайта:
- mobile viewport: {signals.has_mobile_viewport}
- contact form: {signals.has_contact_form}
- catalog: {signals.has_online_catalog}
- personal account: {signals.has_personal_account}
- online payment: {signals.has_online_payment}
- crm hints: {signals.crm_hints}
- technical issues: {signals.technical_issues}
Фрагмент текста: {parsed.raw_text_sample[:2500]}
"""

    def _fallback(self, company_name: str, parsed: ParsedCompany) -> AIAnalysisResult:
        issues: list[str] = []
        needs: list[str] = []
        evidence: list[FactReference] = []
        s = parsed.signals
        if not s.has_personal_account:
            issues.append("Не обнаружен личный кабинет на сайте")
            needs.append("Разработка личного кабинета")
            evidence.append(FactReference(fact="Нет признаков личного кабинета", source_url=parsed.source_url))
        if s.has_online_catalog and not s.has_online_payment:
            issues.append("Есть каталог, но нет признаков онлайн-оплаты")
            needs.append("Автоматизация заказов и оплаты")
        if not s.crm_hints:
            issues.append("Не видно интеграции с CRM")
            needs.append("Интеграция CRM")
        if not needs:
            needs.append("Разработка или доработка веб-сервиса")
        return AIAnalysisResult(
            business_summary=f"{company_name}: данные собраны эвристически без LLM.",
            identified_issues=issues or ["Недостаточно данных для глубокого анализа"],
            assumed_needs=needs,
            recommended_service=needs[0],
            rationale="Оценка на основе технических сигналов сайта",
            confidence=0.45,
            evidence=evidence,
        )
