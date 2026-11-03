import asyncio
import logging

from app.db.session import AsyncSessionLocal
from app.services.orchestrator import Orchestrator
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="search.run_pipeline")
def run_search_task(task_id: int) -> None:
    asyncio.run(_run_async(task_id))


async def _run_async(task_id: int) -> None:
    orchestrator = Orchestrator()
    async with AsyncSessionLocal() as session:
        await orchestrator.run_search_pipeline(session, task_id)
    logger.info("Search task %s finished", task_id)
