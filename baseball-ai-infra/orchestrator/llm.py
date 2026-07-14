"""
Natural-language command parser for the Baseball AI system.

This module calls an OpenAI-compatible language-model server,
such as vLLM, and converts user text into a validated tool request.
"""

import json
from dataclasses import dataclass
from typing import Any

import httpx

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
    TIMEOUT_SECONDS,
)


class LLMError(RuntimeError):
    """Raised when the language-model request or response is invalid."""


@dataclass(frozen=True)
class ToolRequest:
    """
    A validated command produced by the language model.
    """

    action: str
    arguments: dict[str, Any]


SYSTEM_PROMPT = """
You are the command parser for a Baseball AI orchestrator.

Convert the user's request into exactly one JSON object.

Currently, the only supported action is:

{
  "action": "analyze_player",
  "arguments": {
    "name": "Player Name",
    "avg": 0.300,
    "obp": 0.400,
    "slg": 0.500
  }
}

Rules:
1. Return JSON only.
2. Do not use Markdown.
3. Do not include explanations.
4. Do not invent missing statistics.
5. AVG, OBP, and SLG must be decimal numbers between 0 and 1.
6. Use the exact action name "analyze_player".
7. The player's name must be a non-empty string.
8. If required information is missing, return:

{
  "error": "A clear description of the missing information."
}
""".strip()


class BaseballLLM:
    """
    Client for an OpenAI-compatible language-model server.
    """

    def __init__(
        self,
        base_url: str = LLM_BASE_URL,
        model_name: str = LLM_MODEL_NAME,
        api_key: str = LLM_API_KEY,
        timeout: float = TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name.strip()
        self._api_key = api_key
        self._timeout = timeout

    def _require_model_name(self) -> str:
        """
        Return the configured model name or raise a clear error.
        """
        if not self._model_name:
            raise LLMError(
                "LLM_MODEL_NAME is not configured. "
                "Check the available models at /v1/models and export "
                "LLM_MODEL_NAME before running the orchestrator."
            )

        return self._model_name

    @staticmethod
    def _remove_code_fence(text: str) -> str:
        """
        Remove accidental Markdown JSON fences from a model response.
        """
        cleaned = text.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json"):].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[len("```"):].strip()

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        return cleaned

    @staticmethod
    def _validate_rate(
        field_name: str,
        value: Any,
    ) -> float:
        """
        Validate a baseball rate statistic.
        """
        if isinstance(value, bool):
            raise LLMError(
                f"LLM returned an invalid {field_name} value."
            )

        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as error:
            raise LLMError(
                f"LLM returned a non-numeric {field_name} value."
            ) from error

        if not 0 <= numeric_value <= 1:
            raise LLMError(
                f"LLM returned {field_name} outside the range 0 to 1."
            )

        return numeric_value

    @classmethod
    def _validate_response(
        cls,
        data: Any,
    ) -> ToolRequest:
        """
        Validate the JSON object returned by the model.
        """
        if not isinstance(data, dict):
            raise LLMError(
                "LLM response must be a JSON object."
            )

        model_error = data.get("error")

        if isinstance(model_error, str) and model_error.strip():
            raise LLMError(model_error.strip())

        action = data.get("action")
        arguments = data.get("arguments")

        if action != "analyze_player":
            raise LLMError(
                f"Unsupported LLM action: {action!r}"
            )

        if not isinstance(arguments, dict):
            raise LLMError(
                "LLM response is missing an arguments object."
            )

        name = arguments.get("name")

        if not isinstance(name, str) or not name.strip():
            raise LLMError(
                "LLM response is missing a valid player name."
            )

        validated_arguments = {
            "name": name.strip(),
            "avg": cls._validate_rate(
                "avg",
                arguments.get("avg"),
            ),
            "obp": cls._validate_rate(
                "obp",
                arguments.get("obp"),
            ),
            "slg": cls._validate_rate(
                "slg",
                arguments.get("slg"),
            ),
        }

        return ToolRequest(
            action=action,
            arguments=validated_arguments,
        )

    async def parse_request(
        self,
        user_text: str,
    ) -> ToolRequest:
        """
        Convert natural-language text into a validated tool request.
        """
        if not isinstance(user_text, str):
            raise ValueError(
                "User text must be a string."
            )

        cleaned_user_text = user_text.strip()

        if not cleaned_user_text:
            raise ValueError(
                "User text cannot be empty."
            )

        model_name = self._require_model_name()

        url = f"{self._base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_name,
            "temperature": LLM_TEMPERATURE,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": cleaned_user_text,
                },
            ],
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                trust_env=False,
            ) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

                response.raise_for_status()

        except httpx.TimeoutException as error:
            raise LLMError(
                f"LLM request timed out: {url}"
            ) from error

        except httpx.ConnectError as error:
            raise LLMError(
                f"Could not connect to the LLM server: {url}"
            ) from error

        except httpx.HTTPStatusError as error:
            raise LLMError(
                "LLM server returned "
                f"HTTP {error.response.status_code}: "
                f"{error.response.text}"
            ) from error

        try:
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]
        except (
            ValueError,
            KeyError,
            IndexError,
            TypeError,
        ) as error:
            raise LLMError(
                "LLM server returned an invalid chat-completion response."
            ) from error

        if not isinstance(content, str):
            raise LLMError(
                "LLM response content was not text."
            )

        cleaned_content = self._remove_code_fence(content)

        try:
            parsed_content = json.loads(cleaned_content)
        except json.JSONDecodeError as error:
            raise LLMError(
                "LLM did not return valid JSON. "
                f"Raw response: {content}"
            ) from error

        return self._validate_response(parsed_content)
