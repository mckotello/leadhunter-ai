from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.domain import SearchCreate, SearchTaskRead
from app.services.orchestrator import Orchestrator
from app.tasks.search_tasks import run_search_task

router = APIRouter()
orchestrator = Orchestrator()


@router.post("/search", response_model=SearchTaskRead)
async def start_search(payload: SearchCreate, db: AsyncSession = Depends(get_db)):
    task = await orchestrator.create_search_task(db, payload)
    run_search_task.delay(task.id)
    return SearchTaskRead(
        id=task.id,
        query=task.query,
        filters=task.filters,
        status=task.status.value,
        total_found=task.total_found,
        total_processed=task.total_processed,
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )


@router.get("/search/{task_id}", response_model=SearchTaskRead)
async def get_search_status(task_id: int, db: AsyncSession = Depends(get_db)):
    from app.models.entities import SearchTask

    task = await db.get(SearchTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return SearchTaskRead(
        id=task.id,
        query=task.query,
        filters=task.filters,
        status=task.status.value,
        total_found=task.total_found,
        total_processed=task.total_processed,
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )
