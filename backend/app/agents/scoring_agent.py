from app.models.entities import LeadTemperature
from app.schemas.domain import AIAnalysisResult, ScoringResult


class ScoringAgent:
    WEIGHTS = {
        "audience_fit": 25,
        "development_need": 30,
        "automation_potential": 20,
        "contacts": 10,
        "freshness": 15,
    }

    def score(
        self,
        niche: str,
        industry: str | None,
        analysis: AIAnalysisResult,
        has_phone: bool,
        has_email: bool,
        has_website: bool,
    ) -> ScoringResult:
        breakdown: dict[str, int] = {}

        audience = 12
        if industry and niche.lower() in (industry or "").lower():
            audience = self.WEIGHTS["audience_fit"]
        elif industry:
            audience = 18
        breakdown["audience_fit"] = min(audience, self.WEIGHTS["audience_fit"])

        dev_need = min(self.WEIGHTS["development_need"], 10 + len(analysis.assumed_needs) * 6)
        breakdown["development_need"] = dev_need

        auto = 8
        text = " ".join(analysis.assumed_needs + analysis.identified_issues).lower()
        if any(w in text for w in ("автомат", "crm", "кабинет", "интеграц")):
            auto = self.WEIGHTS["automation_potential"]
        breakdown["automation_potential"] = auto

        contacts = 0
        if has_phone:
            contacts += 5
        if has_email:
            contacts += 5
        breakdown["contacts"] = contacts

        freshness = self.WEIGHTS["freshness"] if has_website else 5
        breakdown["freshness"] = freshness

        total = min(100, sum(breakdown.values()))
        temp = self._temperature(total)
        explanation = (
            f"Итог {total}/100: аудитория {breakdown['audience_fit']}, "
            f"потребность {breakdown['development_need']}, автоматизация {breakdown['automation_potential']}, "
            f"контакты {breakdown['contacts']}, актуальность {breakdown['freshness']}."
        )
        return ScoringResult(score=total, temperature=temp.value, explanation=explanation, breakdown=breakdown)

    def _temperature(self, score: int) -> LeadTemperature:
        if score >= 80:
            return LeadTemperature.HOT
        if score >= 60:
            return LeadTemperature.WARM
        if score >= 40:
            return LeadTemperature.POTENTIAL
        return LeadTemperature.LOW
