from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate_json(self, prompt: str) -> dict:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        request = Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        payload = self._post_with_retry(request)

        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)

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

        raise RuntimeError(f"Gemini request failed: {last_error}") from last_error
