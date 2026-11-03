from unittest.mock import patch

from app.tasks import search_tasks


def test_celery_task_runs_async_pipeline():
    with patch("app.tasks.search_tasks.asyncio.run") as run_mock:
        search_tasks.run_search_task(42)
    run_mock.assert_called_once()
