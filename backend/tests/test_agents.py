from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.ai_analyst import AIAnalystAgent
from app.agents.offer_agent import OfferAgent
from app.agents.parser_agent import ParsedCompany, ParserAgent, SiteSignals
from app.agents.search_agent import SearchAgent
from app.integrations.llm.client import LLMError
from app.schemas.domain import AIAnalysisResult, NeedType, OfferDraft, SearchCreate
from app.utils.ssrf import SSRFError


@pytest.mark.asyncio
async def test_parser_agent_blocks_ssrf():
    agent = ParserAgent()
    with patch("app.agents.parser_agent.validate_public_url", side_effect=SSRFError("blocked")):
        result = await agent.parse("http://127.0.0.1", "Co")
    assert result.name == "Co"


@pytest.mark.asyncio
async def test_parser_agent_parses_html():
    agent = ParserAgent()
    html = (
        "<html><head><title>Acme</title>"
        "<meta name='viewport' content='width=device-width'></head>"
        "<body><form></form></body></html>"
    )
    with patch.object(agent, "_fetch_with_retries", new=AsyncMock(return_value=(html, "https://acme.test"))):
        with patch("app.agents.parser_agent.validate_public_url", return_value="https://acme.test"):
            result = await agent.parse("https://acme.test", None)
    assert result.signals.has_contact_form is True
    assert result.signals.has_mobile_viewport is True


def test_search_agent_build_queries_unique():
    agent = SearchAgent()
    payload = SearchCreate(niche="опт", region="Москва", keywords="", need_type=NeedType.CRM_INTEGRATION, limit=10)
    queries = agent.build_queries(payload)
    assert len(queries) == len(set(queries))
    assert any("crm_integration" in q or "опт" in q for q in queries)


@pytest.mark.asyncio
async def test_search_agent_run_uses_provider():
    agent = SearchAgent()
    payload = SearchCreate(niche="opt", region="msk", keywords="", need_type=NeedType.OTHER, limit=3)
    mock_provider = AsyncMock()
    mock_provider.search.return_value = []
    with patch("app.agents.search_agent.get_search_provider", return_value=mock_provider):
        await agent.run(payload)
    mock_provider.search.assert_awaited_once()


def test_ai_analyst_fallback_on_llm_error():
    llm = MagicMock()
    llm.complete_json.side_effect = LLMError("down")
    agent = AIAnalystAgent(llm=llm)
    parsed = ParsedCompany(source_url="https://x.test", signals=SiteSignals())
    result = agent.analyze("Co", parsed, "opt", "other")
    assert result.confidence == 0.45
    assert result.assumed_needs


def test_offer_agent_fallback_on_llm_error():
    llm = MagicMock()
    llm.complete_json.side_effect = LLMError("down")
    agent = OfferAgent(llm=llm)
    analysis = AIAnalysisResult(
        business_summary="s",
        identified_issues=["i"],
        assumed_needs=["n"],
        recommended_service="CRM",
        rationale="r",
        confidence=0.5,
        evidence=[],
    )
    draft = agent.generate("Co", analysis)
    assert isinstance(draft, OfferDraft)
    assert "Co" in draft.introduction
