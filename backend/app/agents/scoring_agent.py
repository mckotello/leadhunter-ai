from app.agents.parser_agent import ParsedCompany
from app.models.entities import LeadTemperature
from app.schemas.domain import AIAnalysisResult, ScoringResult

CRITERION_LABELS = {
    "audience_fit": "Соответствие целевой аудитории (макс. 25)",
    "development_need": "Выявленная потребность в разработке (макс. 30)",
    "automation_potential": "Потенциал автоматизации (макс. 20)",
    "contacts": "Наличие контактов (макс. 10)",
    "freshness": "Актуальность и полнота данных (макс. 15)",
}


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
        parsed: ParsedCompany | None = None,
    ) -> ScoringResult:
        breakdown: dict[str, int] = {}
        details: dict[str, str] = {}

        niche_l = niche.lower().strip()
        industry_l = (industry or "").lower().strip()

        if industry_l and (niche_l in industry_l or industry_l in niche_l):
            audience = self.WEIGHTS["audience_fit"]
            details["audience_fit"] = "Ниша поиска совпадает с указанной отраслью компании."
        elif industry_l:
            audience = 15
            details["audience_fit"] = (
                "Отрасль компании известна, но не совпадает напрямую с нишей поиска."
            )
        else:
            audience = 8
            details["audience_fit"] = "Отрасль компании не указана — частичный балл."
        breakdown["audience_fit"] = min(audience, self.WEIGHTS["audience_fit"])

        need_count = len(analysis.assumed_needs)
        dev_need = min(
            self.WEIGHTS["development_need"],
            int(8 + need_count * 5 + analysis.confidence * 7),
        )
        breakdown["development_need"] = dev_need
        details["development_need"] = (
            f"Выявлено потребностей: {need_count}, уверенность AI: {analysis.confidence:.0%}."
        )

        auto = 6
        text = " ".join(analysis.assumed_needs + analysis.identified_issues).lower()
        if any(w in text for w in ("автомат", "crm", "кабинет", "интеграц", "бот")):
            auto = self.WEIGHTS["automation_potential"]
            details["automation_potential"] = (
                "В анализе есть запрос на автоматизацию, CRM или личный кабинет."
            )
        else:
            details["automation_potential"] = "Явных сигналов автоматизации в анализе не найдено."

        breakdown["automation_potential"] = auto

        contacts = 0
        contact_parts: list[str] = []
        if has_phone:
            contacts += 5
            contact_parts.append("телефон")
        if has_email:
            contacts += 5
            contact_parts.append("email")
        breakdown["contacts"] = contacts
        details["contacts"] = (
            "Найдены контакты: " + (", ".join(contact_parts) if contact_parts else "нет публичных контактов")
        )

        freshness, freshness_detail = self._score_freshness(analysis, parsed)
        breakdown["freshness"] = freshness
        details["freshness"] = freshness_detail

        total = min(100, sum(breakdown.values()))
        temp = self._temperature(total)

        lines = [f"Итоговая оценка: {total}/100 ({temp.value})."]
        for key in self.WEIGHTS:
            lines.append(f"- {CRITERION_LABELS[key]}: {breakdown[key]} — {details[key]}")
        explanation = "\n".join(lines)

        return ScoringResult(
            score=total,
            temperature=temp.value,
            explanation=explanation,
            breakdown=breakdown,
        )

    def _score_freshness(
        self, analysis: AIAnalysisResult, parsed: ParsedCompany | None
    ) -> tuple[int, str]:
        """Актуальность данных — не наличие сайта, а качество собранной информации."""
        points = int(round(analysis.confidence * 8))
        reasons = [f"уверенность AI {analysis.confidence:.0%}"]

        if parsed:
            richness = 0
            if parsed.description:
                richness += 2
                reasons.append("есть описание деятельности")
            if len(parsed.raw_text_sample) >= 500:
                richness += 2
                reasons.append("достаточно контента на странице")
            if parsed.signals.technical_issues or parsed.products_services:
                richness += 1
                reasons.append("есть структурные сигналы сайта")
            if parsed.phone or parsed.email:
                richness += 1
                reasons.append("контакты подтверждены парсером")
            points += min(7, richness)
        else:
            reasons.append("данные парсера недоступны — только AI-анализ")

        points = min(self.WEIGHTS["freshness"], points)
        return points, "Полнота и свежесть intel: " + ", ".join(reasons) + "."

    def _temperature(self, score: int) -> LeadTemperature:
        if score >= 80:
            return LeadTemperature.HOT
        if score >= 60:
            return LeadTemperature.WARM
        if score >= 40:
            return LeadTemperature.POTENTIAL
        return LeadTemperature.LOW
