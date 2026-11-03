import logging

from app.integrations.search.base import SearchHit
from app.integrations.search.providers import get_search_provider
from app.schemas.domain import SearchCreate

logger = logging.getLogger(__name__)


class SearchAgent:
    def build_queries(self, payload: SearchCreate) -> list[str]:
        base = f"{payload.niche} {payload.region} {payload.keywords}".strip()
        queries = [
            base,
            f"{payload.niche} {payload.region} site",
            f"{payload.niche} {payload.region} компания каталог",
            f"{payload.niche} {payload.region} {payload.need_type.value}",
        ]
        return list(dict.fromkeys(q.strip() for q in queries if q.strip()))

    async def run(self, payload: SearchCreate) -> list[SearchHit]:
        provider = get_search_provider()
        queries = self.build_queries(payload)
        logger.info("Search queries: %s", queries)
        hits = await provider.search(queries, payload.limit)
        return self.deduplicate(hits)

    def deduplicate(self, hits: list[SearchHit]) -> list[SearchHit]:
        seen_urls: set[str] = set()
        seen_names: set[str] = set()
        unique: list[SearchHit] = []
        for hit in hits:
            url_key = (hit.website or hit.source_url).lower().rstrip("/")
            name_key = hit.name.lower().strip()
            if url_key in seen_urls or name_key in seen_names:
                continue
            seen_urls.add(url_key)
            seen_names.add(name_key)
            unique.append(hit)
        return unique
