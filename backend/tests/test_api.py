from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.integrations.search.providers import SerpApiSearchProvider
from app.main import app


@pytest.fixture
async def api_client():
    session = AsyncMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoint(api_client):
    resp = await api_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_search_endpoint_enqueues_task(api_client):
    fake_task = MagicMock()
    fake_task.id = 1
    fake_task.query = "q"
    fake_task.filters = {}
    fake_task.status = MagicMock(value="pending")
    fake_task.total_found = 0
    fake_task.total_processed = 0
    fake_task.error_message = None
    fake_task.created_at = datetime.now(timezone.utc)
    fake_task.completed_at = None

    with patch("app.api.search.orchestrator.create_search_task", new=AsyncMock(return_value=fake_task)):
        with patch("app.api.search.run_search_task.delay") as delay_mock:
            resp = await api_client.post(
                "/api/search",
                json={
                    "niche": "опт",
                    "region": "Москва",
                    "keywords": "",
                    "need_type": "other",
                    "limit": 5,
                },
            )
    assert resp.status_code == 200
    delay_mock.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_serpapi_provider_continues_after_http_error():
    provider = SerpApiSearchProvider()
    response = httpx.Response(500, text="error", request=httpx.Request("GET", "https://serpapi.com/search.json"))
    with patch("app.integrations.search.providers.settings.serpapi_api_key", "test-key"):
        with patch(
            "httpx.AsyncClient.get",
            new=AsyncMock(side_effect=httpx.HTTPStatusError("fail", request=response.request, response=response)),
        ):
            hits = await provider.search(["query"], 5)
    assert hits == []
