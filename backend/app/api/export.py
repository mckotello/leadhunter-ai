from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.export_service import export_leads_csv, export_leads_xlsx

router = APIRouter()


@router.get("/export")
async def export_leads(
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
    db: AsyncSession = Depends(get_db),
):
    if format == "xlsx":
        content = await export_leads_xlsx(db)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=leads.xlsx"},
        )
    csv_data = await export_leads_csv(db)
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
