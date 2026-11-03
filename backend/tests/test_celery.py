from unittest.mock import AsyncMock, patch

from app.tasks import search_tasks


def test_celery_task_runs_async_pipeline():
    with patch("app.tasks.search_tasks._run_async", new=AsyncMock()) as pipeline_mock:
        with patch("app.tasks.search_tasks.asyncio.run") as run_mock:
            run_mock.side_effect = lambda coro: coro.close()
            search_tasks.run_search_task(42)
    run_mock.assert_called_once()
    pipeline_mock.assert_called_once_with(42)
