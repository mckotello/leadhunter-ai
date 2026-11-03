from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.domain import CompanyRead, DashboardStats
from app.services.orchestrator import DashboardService

router = APIRouter()
dashboard_service = DashboardService()


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(db: AsyncSession = Depends(get_db)):
    data = await dashboard_service.stats(db)
    return DashboardStats(
        total_companies=data["total_companies"],
        analyzed_leads=data["analyzed_leads"],
        hot_leads=data["hot_leads"],
        warm_leads=data["warm_leads"],
        search_tasks=data["search_tasks"],
        temperature_distribution=data["temperature_distribution"],
        recent_companies=[CompanyRead.model_validate(c) for c in data["recent_companies"]],
    )
