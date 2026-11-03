import pytest

from app.agents.search_agent import SearchAgent
from app.integrations.search.base import SearchHit
from app.schemas.domain import extract_domain, normalize_company_name
from app.utils.ssrf import SSRFError, validate_public_url


def test_normalize_company_name():
    assert "торговый дом" in normalize_company_name('ООО «Торговый дом»')


def test_extract_domain():
    assert extract_domain("https://www.example.com/page") == "example.com"


def test_search_deduplicate():
    agent = SearchAgent()
    hits = [
        SearchHit("A", "https://x.com", None, "https://x.com", "mock"),
        SearchHit("A", "https://x.com", None, "https://x.com", "mock"),
        SearchHit("B", "https://y.com", None, "https://y.com", "mock"),
    ]
    assert len(agent.deduplicate(hits)) == 2


def test_ssrf_blocks_localhost():
    with pytest.raises(SSRFError):
        validate_public_url("http://127.0.0.1/admin")


def test_ssrf_allows_public_https():
    url = validate_public_url("https://example.com")
    assert url.startswith("https://example.com")
