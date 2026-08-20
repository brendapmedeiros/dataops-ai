from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dataops_ai.models import LLMMetadata


GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


@dataclass(frozen=True)
class GeminiResult:
    data: dict
    metadata: LLMMetadata


@dataclass(frozen=True)
class GeminiClient:
    api_key: str
    model: str
    store_interaction: bool = True
    prompt_version: str = "quality-diagnosis-v1"

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        tools: list[dict] | None = None,
        tool_handlers: dict[str, Callable[[dict], dict]] | None = None,
    ) -> GeminiResult:
        started_at = time.perf_counter()

        try:
            first_payload = self._create_interaction(
                [{"type": "user_input", "content": prompt}],
                schema,
                tools=tools,
            )
            payload = self._finish_tool_calls(first_payload, schema, tools, tool_handlers)
            text = _extract_interaction_text(payload)
            metadata = _metadata_from_interaction(
                payload,
                self.model,
                self.store_interaction,
                self.prompt_version,
                started_at,
                tools or [],
                _tool_call_names(first_payload),
                previous_interaction_id=first_payload.get("id") if payload is not first_payload else None,
            )
            return GeminiResult(json.loads(text), metadata)
        except Exception as exc:
            # A Interactions API é o caminho principal. O fallback existe para não travar o estudo.
            fallback_reason = str(exc)

        payload = self._generate_content(prompt)
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        metadata = LLMMetadata(
            provider="gemini",
            model=self.model,
            api="generateContent",
            response_format="json",
            prompt_version=self.prompt_version,
            store_interaction=False,
            latency_ms=_elapsed_ms(started_at),
            fallback_reason=f"Interactions indisponível: {fallback_reason}",
        )
        return GeminiResult(json.loads(text), metadata)

    def _create_interaction(
        self,
        input_payload: object,
        schema: dict[str, Any],
        tools: list[dict] | None = None,
        previous_interaction_id: str | None = None,
    ) -> dict:
        body = {
            "model": self.model,
            "input": input_payload,
            "store": self.store_interaction,
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": schema,
            },
            "generation_config": {
                "temperature": 0.2,
            },
        }
        if tools:
            body["tools"] = tools
        if previous_interaction_id:
            body["previous_interaction_id"] = previous_interaction_id

        request = Request(
            f"{GEMINI_API_BASE_URL}/interactions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        return self._post_with_retry(request)

    def _finish_tool_calls(
        self,
        payload: dict,
        schema: dict[str, Any],
        tools: list[dict] | None,
        tool_handlers: dict[str, Callable[[dict], dict]] | None,
    ) -> dict:
        function_calls = _function_calls(payload)
        if not function_calls or not tool_handlers:
            return payload

        function_results = []
        for call in function_calls:
            name = call.get("name")
            handler = tool_handlers.get(name)
            if not name or not handler:
                continue
            result = handler(call.get("arguments") or {})
            function_results.append(
                {
                    "type": "function_result",
                    "name": name,
                    "call_id": call.get("id"),
                    "result": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                }
            )

        if not function_results:
            return payload

        return self._create_interaction(
            function_results,
            schema,
            tools=tools,
            previous_interaction_id=payload.get("id"),
        )

    def _generate_content(self, prompt: str) -> dict:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
        }
        request = Request(
            f"{GEMINI_API_BASE_URL}/models/{self.model}:generateContent?key={self.api_key}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._post_with_retry(request)

    def _post_with_retry(self, request: Request, attempts: int = 3) -> dict:
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                with urlopen(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504} or attempt == attempts:
                    break
            except (URLError, TimeoutError) as exc:
                last_error = exc
                if attempt == attempts:
                    break

            time.sleep(attempt)

        raise RuntimeError(f"Falha na chamada do Gemini: {last_error}") from last_error


def _metadata_from_interaction(
    payload: dict,
    model: str,
    store_interaction: bool,
    prompt_version: str,
    started_at: float,
    tools: list[dict],
    tool_calls: list[str],
    previous_interaction_id: str | None,
) -> LLMMetadata:
    steps = payload.get("steps", [])
    return LLMMetadata(
        provider="gemini",
        model=model,
        api="interactions",
        interaction_id=payload.get("id"),
        previous_interaction_id=previous_interaction_id,
        response_format="json_schema",
        prompt_version=prompt_version,
        store_interaction=store_interaction,
        latency_ms=_elapsed_ms(started_at),
        step_types=[step.get("type", "unknown") for step in steps if isinstance(step, dict)],
        tool_names=[tool.get("name", "unknown") for tool in tools],
        tool_calls=tool_calls,
    )


def _extract_interaction_text(payload: dict) -> str:
    if payload.get("output_text"):
        return str(payload["output_text"])

    for step in payload.get("steps", []):
        if not isinstance(step, dict):
            continue
        if step.get("type") != "model_output":
            continue
        text = _extract_text_from_step(step)
        if text:
            return text

    raise RuntimeError("Gemini não retornou texto estruturado na interaction.")


def _function_calls(payload: dict) -> list[dict]:
    return [
        step
        for step in payload.get("steps", [])
        if isinstance(step, dict) and step.get("type") == "function_call"
    ]


def _tool_call_names(payload: dict) -> list[str]:
    return [call.get("name", "unknown") for call in _function_calls(payload)]


def _extract_text_from_step(step: dict) -> str | None:
    for key in ("content", "output", "parts"):
        value = step.get(key)
        text = _extract_text(value)
        if text:
            return text
    return None


def _extract_text(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        for nested in value.values():
            text = _extract_text(nested)
            if text:
                return text
    if isinstance(value, list):
        for item in value:
            text = _extract_text(item)
            if text:
                return text
    return None


def _elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)
