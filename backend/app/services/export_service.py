import csv
import io
from datetime import datetime

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import Lead


async def export_leads_csv(session: AsyncSession) -> str:
    result = await session.execute(select(Lead).options(selectinload(Lead.company)).order_by(Lead.score.desc()))
    leads = result.scalars().all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "lead_id",
            "company",
            "website",
            "industry",
            "score",
            "temperature",
            "status",
            "needs",
            "recommended",
            "phone",
            "email",
        ]
    )
    for lead in leads:
        c = lead.company
        writer.writerow(
            [
                lead.id,
                c.name if c else "",
                c.website if c else "",
                c.industry if c else "",
                lead.score or "",
                lead.temperature.value if lead.temperature else "",
                lead.status.value,
                "; ".join(lead.detected_needs or []),
                "; ".join(lead.recommended_services or []),
                c.phone if c else "",
                c.email if c else "",
            ]
        )
    return buffer.getvalue()


async def export_leads_xlsx(session: AsyncSession) -> bytes:
    result = await session.execute(select(Lead).options(selectinload(Lead.company)).order_by(Lead.score.desc()))
    leads = result.scalars().all()
    wb = Workbook()
    ws = wb.active
    ws.title = "leads"
    ws.append(
        [
            "lead_id",
            "company",
            "website",
            "score",
            "status",
            "updated_at",
        ]
    )
    for lead in leads:
        c = lead.company
        ws.append(
            [
                lead.id,
                c.name if c else "",
                c.website if c else "",
                lead.score,
                lead.status.value,
                lead.updated_at.isoformat() if isinstance(lead.updated_at, datetime) else "",
            ]
        )
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
