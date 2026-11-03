import json
import logging
from typing import TypeVar

from openai import APIConnectionError, APITimeoutError, APIStatusError, OpenAI
from pydantic import BaseModel, ValidationError

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Ошибка вызова LLM-провайдера."""


class LLMClient:
    def __init__(self) -> None:
        self._client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout,
        )
        self.model = settings.llm_model

    def complete_json(self, system: str, user: str, schema: type[T]) -> T:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
        except APITimeoutError as exc:
            logger.error("LLM timeout (model=%s): %s", self.model, exc)
            raise LLMError("Превышено время ожидания LLM") from exc
        except APIConnectionError as exc:
            logger.error("LLM connection error: %s", exc)
            raise LLMError("Не удалось подключиться к LLM") from exc
        except APIStatusError as exc:
            logger.error("LLM HTTP %s: %s", exc.status_code, exc.message)
            raise LLMError(f"LLM вернула ошибку {exc.status_code}") from exc

        content = response.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON, wrapping as text field")
            data = {"business_summary": content}
        try:
            return schema.model_validate(data)
        except ValidationError as exc:
            logger.error("LLM JSON не соответствует схеме: %s", exc)
            raise LLMError("Невалидный структурированный ответ LLM") from exc

    def complete_text(self, system: str, user: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.4,
            )
        except (APITimeoutError, APIConnectionError, APIStatusError) as exc:
            logger.error("LLM text completion failed: %s", exc)
            raise LLMError("Ошибка генерации текста LLM") from exc
        return response.choices[0].message.content or ""
