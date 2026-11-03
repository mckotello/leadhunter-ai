from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.entities import LeadStatus
from app.schemas.domain import (
    CompanyRead,
    GeneratedOfferRead,
    LeadDetail,
    LeadListItem,
    LeadNoteCreate,
    LeadNoteRead,
    LeadUpdate,
    SourceRead,
)
from app.services.orchestrator import LeadService, Orchestrator

router = APIRouter()
lead_service = LeadService()
orchestrator = Orchestrator()


@router.get("/leads", response_model=list[LeadListItem])
async def list_leads(
    status: str | None = None,
    min_score: int | None = Query(default=None, ge=0, le=100),
    q: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    leads = await lead_service.list_leads(db, status=status, min_score=min_score, q=q, limit=limit, offset=offset)
    items: list[LeadListItem] = []
    for lead in leads:
        needs = lead.detected_needs or []
        items.append(
            LeadListItem(
                id=lead.id,
                company_id=lead.company_id,
                company_name=lead.company.name,
                industry=lead.company.industry,
                primary_need=needs[0] if needs else None,
                score=lead.score,
                temperature=lead.temperature.value if lead.temperature else None,
                status=lead.status.value,
            )
        )
    return items


@router.get("/leads/{lead_id}", response_model=LeadDetail)
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    lead = await lead_service.get_lead_detail(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Лид не найден")
    return LeadDetail(
        id=lead.id,
        score=lead.score,
        temperature=lead.temperature.value if lead.temperature else None,
        status=lead.status.value,
        detected_needs=lead.detected_needs,
        recommended_services=lead.recommended_services,
        ai_analysis=lead.ai_analysis,
        score_explanation=lead.score_explanation,
        confidence=lead.confidence,
        company=CompanyRead.model_validate(lead.company),
        sources=[SourceRead.model_validate(s) for s in lead.company.sources],
        notes=[LeadNoteRead.model_validate(n) for n in lead.notes],
        offers=[GeneratedOfferRead.model_validate(o) for o in lead.offers],
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@router.patch("/leads/{lead_id}", response_model=LeadDetail)
async def update_lead(lead_id: int, payload: LeadUpdate, db: AsyncSession = Depends(get_db)):
    lead = await lead_service.get_lead_detail(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Лид не найден")
    if payload.status is not None:
        try:
            lead.status = LeadStatus(payload.status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Неверный статус") from exc
    if payload.score is not None:
        lead.score = payload.score
    await db.commit()
    return await get_lead(lead_id, db)


@router.post("/leads/{lead_id}/analyze")
async def analyze_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    try:
        lead = await orchestrator.reanalyze_lead(db, lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"lead_id": lead.id, "score": lead.score, "status": lead.status.value}


@router.post("/leads/{lead_id}/offer", response_model=GeneratedOfferRead)
async def create_offer(lead_id: int, db: AsyncSession = Depends(get_db)):
    try:
        offer = await orchestrator.generate_offer(db, lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GeneratedOfferRead.model_validate(offer)


@router.post("/leads/{lead_id}/notes", response_model=LeadNoteRead)
async def add_note(lead_id: int, payload: LeadNoteCreate, db: AsyncSession = Depends(get_db)):
    from app.models.entities import LeadNote

    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Лид не найден")
    note = LeadNote(lead_id=lead_id, content=payload.content)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return LeadNoteRead.model_validate(note)
