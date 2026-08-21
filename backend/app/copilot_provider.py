from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from .copilot_config import CopilotConfig


@dataclass(frozen=True)
class CopilotGenerationRequest:
    system_prompt: str
    user_prompt: str


@dataclass(frozen=True)
class CopilotGenerationResult:
    answer: str
    provider: str
    model: str


class CopilotProviderError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CopilotProvider(Protocol):
    def generate(self, request: CopilotGenerationRequest) -> CopilotGenerationResult: ...


class OllamaCopilotProvider:
    def __init__(
        self,
        config: CopilotConfig,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._config = config
        self._client = client

    def generate(self, request: CopilotGenerationRequest) -> CopilotGenerationResult:
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "stream": False,
            "options": {"temperature": self._config.temperature},
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            if self._client is not None:
                response = self._client.post(
                    f"{self._config.base_url}/chat",
                    json=payload,
                    headers=headers,
                    timeout=self._config.timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self._config.timeout_seconds) as client:
                    response = client.post(
                        f"{self._config.base_url}/chat",
                        json=payload,
                        headers=headers,
                    )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise CopilotProviderError("provider timeout") from exc
        except httpx.HTTPStatusError as exc:
            reason = {
                401: "provider authentication failed",
                403: "provider authorization failed",
                429: "provider quota or rate limit reached",
            }.get(exc.response.status_code, "provider unavailable")
            raise CopilotProviderError(reason) from exc
        except httpx.HTTPError as exc:
            raise CopilotProviderError("provider unavailable") from exc

        try:
            content = str(response.json()["message"]["content"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise CopilotProviderError("provider returned an invalid response") from exc
        if not content:
            raise CopilotProviderError("provider returned an empty response")
        return CopilotGenerationResult(
            answer=content,
            provider=self._config.provider,
            model=self._config.model,
        )

    def available_models(self) -> list[str]:
        headers = {"Authorization": f"Bearer {self._config.api_key}"}
        try:
            if self._client is not None:
                response = self._client.get(
                    f"{self._config.base_url}/tags",
                    headers=headers,
                    timeout=self._config.timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self._config.timeout_seconds) as client:
                    response = client.get(
                        f"{self._config.base_url}/tags",
                        headers=headers,
                    )
            response.raise_for_status()
            models = response.json()["models"]
            names = [str(model["name"]).strip() for model in models]
        except httpx.TimeoutException as exc:
            raise CopilotProviderError("provider timeout") from exc
        except httpx.HTTPStatusError as exc:
            reason = {
                401: "provider authentication failed",
                403: "provider authorization failed",
                429: "provider quota or rate limit reached",
            }.get(exc.response.status_code, "provider unavailable")
            raise CopilotProviderError(reason) from exc
        except httpx.HTTPError as exc:
            raise CopilotProviderError("provider unavailable") from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise CopilotProviderError("provider returned an invalid model list") from exc
        return sorted({name for name in names if name})

    def validate_configured_model(self) -> None:
        if self._config.model not in self.available_models():
            raise CopilotProviderError("configured model is unavailable")


def configured_provider(config: CopilotConfig) -> CopilotProvider | None:
    if not config.enabled or not config.api_key:
        return None
    if config.provider != "ollama":
        raise ValueError(f"Unsupported Copilot provider: {config.provider}")
    return OllamaCopilotProvider(config)
