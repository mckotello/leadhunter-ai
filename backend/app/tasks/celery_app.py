from celery import Celery

from app.config import settings

celery_app = Celery("leadhunter", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"

from app.tasks import search_tasks as _search_tasks  # noqa: E402, F401
