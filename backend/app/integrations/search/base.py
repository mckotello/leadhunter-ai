from dataclasses import dataclass


@dataclass
class SearchHit:
    name: str
    website: str | None
    snippet: str | None
    source_url: str
    source_type: str


class SearchProvider:
    async def search(self, queries: list[str], limit: int) -> list[SearchHit]:
        raise NotImplementedError
