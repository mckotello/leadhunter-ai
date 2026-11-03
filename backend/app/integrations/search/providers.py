import logging
from urllib.parse import quote_plus

import httpx

from app.config import settings
from app.integrations.search.base import SearchHit, SearchProvider

logger = logging.getLogger(__name__)


class MockSearchProvider(SearchProvider):
    """Демо-провайдер для MVP без внешнего API."""

    async def search(self, queries: list[str], limit: int) -> list[SearchHit]:
        niche = queries[0] if queries else "компания"
        hits: list[SearchHit] = []
        for i in range(min(limit, 25)):
            idx = i + 1
            hits.append(
                SearchHit(
                    name=f"Demo {niche} #{idx}",
                    website=f"https://example-{idx}.com",
                    snippet=f"Пример компании в нише {niche}",
                    source_url=f"https://search.mock/results?q={quote_plus(niche)}&p={idx}",
                    source_type="mock_search",
                )
            )
        return hits


class SerpApiSearchProvider(SearchProvider):
    async def search(self, queries: list[str], limit: int) -> list[SearchHit]:
        if not settings.serpapi_api_key:
            raise RuntimeError("SERPAPI_API_KEY не задан")

        hits: list[SearchHit] = []
        seen: set[str] = set()
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            for query in queries:
                if len(hits) >= limit:
                    break
                try:
                    resp = await client.get(
                        "https://serpapi.com/search.json",
                        params={
                            "engine": "google",
                            "q": query,
                            "api_key": settings.serpapi_api_key,
                            "num": min(10, limit),
                        },
                    )
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    logger.error(
                        "SerpAPI HTTP %s для запроса %r: %s",
                        exc.response.status_code,
                        query,
                        exc.response.text[:200],
                    )
                    continue
                except httpx.RequestError as exc:
                    logger.error("SerpAPI сетевая ошибка для %r: %s", query, exc)
                    continue

                data = resp.json()
                for item in data.get("organic_results", []):
                    link = item.get("link")
                    title = item.get("title") or "Без названия"
                    if not link or link in seen:
                        continue
                    seen.add(link)
                    hits.append(
                        SearchHit(
                            name=title,
                            website=link,
                            snippet=item.get("snippet"),
                            source_url=link,
                            source_type="serpapi",
                        )
                    )
                    if len(hits) >= limit:
                        break
        return hits[:limit]


def get_search_provider() -> SearchProvider:
    provider = settings.search_provider.lower()
    if provider == "serpapi":
        return SerpApiSearchProvider()
    return MockSearchProvider()
