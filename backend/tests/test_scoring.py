from app.agents.parser_agent import ParsedCompany, SiteSignals
from app.agents.scoring_agent import ScoringAgent
from app.schemas.domain import AIAnalysisResult


def _analysis(**kwargs) -> AIAnalysisResult:
    base = dict(
        business_summary="test",
        identified_issues=["Нет личного кабинета"],
        assumed_needs=["Разработка личного кабинета"],
        recommended_service="Личный кабинет",
        rationale="test",
        confidence=0.8,
        evidence=[],
    )
    base.update(kwargs)
    return AIAnalysisResult(**base)


def test_scoring_freshness_not_tied_to_website_flag():
    agent = ScoringAgent()
    rich = ParsedCompany(
        description="Описание",
        raw_text_sample="x" * 600,
        signals=SiteSignals(technical_issues=["issue"]),
        phone="+79990001122",
    )
    without_site_flag = agent.score(
        niche="торговля",
        industry="торговля",
        analysis=_analysis(confidence=0.9),
        has_phone=True,
        has_email=True,
        parsed=None,
    )
    with_parsed = agent.score(
        niche="торговля",
        industry="торговля",
        analysis=_analysis(confidence=0.9),
        has_phone=True,
        has_email=True,
        parsed=rich,
    )
    assert with_parsed.breakdown["freshness"] >= without_site_flag.breakdown["freshness"]
    assert "наличие сайта" not in with_parsed.explanation.lower()


def test_scoring_explanation_lists_each_criterion():
    agent = ScoringAgent()
    result = agent.score(
        niche="опт",
        industry="оптовая торговля",
        analysis=_analysis(assumed_needs=["CRM", "Автоматизация"], confidence=0.7),
        has_phone=True,
        has_email=False,
        parsed=ParsedCompany(description="desc", raw_text_sample="y" * 400),
    )
    assert result.score <= 100
    assert "Соответствие целевой аудитории" in result.explanation
    assert "Актуальность и полнота данных" in result.explanation
    assert sum(result.breakdown.values()) >= result.score


def test_scoring_contacts_partial():
    agent = ScoringAgent()
    result = agent.score(
        niche="it",
        industry=None,
        analysis=_analysis(),
        has_phone=False,
        has_email=True,
        parsed=None,
    )
    assert result.breakdown["contacts"] == 5
