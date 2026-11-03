import json
import logging

from app.config import settings
from app.integrations.llm.client import LLMClient, LLMError
from app.schemas.domain import AIAnalysisResult, OfferDraft

logger = logging.getLogger(__name__)


class OfferAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def generate(self, company_name: str, analysis: AIAnalysisResult) -> OfferDraft:
        system = (
            "Сформируй черновик коммерческого предложения для B2B IT-студии. "
            "Не обещай автоматическую отправку. JSON: introduction, business_problem, "
            "proposed_solution, expected_benefit, first_message_draft"
        )
        user = json.dumps(
            {
                "company": company_name,
                "studio": settings.studio_name,
                "services": settings.studio_services,
                "analysis": analysis.model_dump(),
            },
            ensure_ascii=False,
        )
        try:
            return self.llm.complete_json(system, user, OfferDraft)
        except LLMError as exc:
            logger.warning("Offer generation LLM error, fallback: %s", exc)
            return self._fallback(company_name, analysis)
        except Exception as exc:
            logger.exception("Offer generation fallback: %s", exc)
            return self._fallback(company_name, analysis)

    def _fallback(self, company_name: str, analysis: AIAnalysisResult) -> OfferDraft:
        service = analysis.recommended_service
        return OfferDraft(
            introduction=f"Здравствуйте! Изучили сайт {company_name}.",
            business_problem="; ".join(analysis.identified_issues[:3]),
            proposed_solution=f"Предлагаем {service}.",
            expected_benefit="Сокращение ручной обработки заявок и рост конверсии.",
            first_message_draft=(
                f"Добрый день! Видим возможность улучшить {service.lower()} для {company_name}. "
                "Можем обсудить короткий созвон?"
            ),
        )

    def format_offer_text(self, draft: OfferDraft) -> str:
        return (
            f"{draft.introduction}\n\n"
            f"Проблема:\n{draft.business_problem}\n\n"
            f"Решение:\n{draft.proposed_solution}\n\n"
            f"Выгода:\n{draft.expected_benefit}\n\n"
            f"Черновик сообщения:\n{draft.first_message_draft}"
        )
