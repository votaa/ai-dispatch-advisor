from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


def _enabled(value: str) -> bool:
    return value.strip().casefold() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class CopilotConfig:
    enabled: bool = False
    provider: str = "ollama"
    model: str = "gpt-oss:120b"
    base_url: str = "https://ollama.com/api"
    api_key: str = ""
    timeout_seconds: float = 60.0
    fallback: str = "rule_based"
    temperature: float = 0.1
    prompt_version: str = "poc-002-v1"
    max_context_records: int = 30

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "CopilotConfig":
        values = environ if environ is not None else os.environ
        config = cls(
            enabled=_enabled(values.get("AIDA_COPILOT_ENABLED", "false")),
            provider=values.get("AIDA_COPILOT_PROVIDER", "ollama").strip().casefold(),
            model=values.get("AIDA_COPILOT_MODEL", "gpt-oss:120b").strip(),
            base_url=values.get(
                "AIDA_COPILOT_BASE_URL", "https://ollama.com/api"
            ).strip().rstrip("/"),
            api_key=values.get("AIDA_COPILOT_API_KEY", "").strip(),
            timeout_seconds=float(values.get("AIDA_COPILOT_TIMEOUT_SECONDS", "60")),
            fallback=values.get("AIDA_COPILOT_FALLBACK", "rule_based").strip().casefold(),
            temperature=float(values.get("AIDA_COPILOT_TEMPERATURE", "0.1")),
            prompt_version=values.get(
                "AIDA_COPILOT_PROMPT_VERSION", "poc-002-v1"
            ).strip(),
            max_context_records=int(
                values.get("AIDA_COPILOT_MAX_CONTEXT_RECORDS", "30")
            ),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not self.provider:
            raise ValueError("AIDA_COPILOT_PROVIDER must not be blank")
        if not self.model:
            raise ValueError("AIDA_COPILOT_MODEL must not be blank")
        if not self.base_url.startswith(("https://", "http://")):
            raise ValueError("AIDA_COPILOT_BASE_URL must be an HTTP(S) URL")
        if self.timeout_seconds <= 0:
            raise ValueError("AIDA_COPILOT_TIMEOUT_SECONDS must be positive")
        if not 0 <= self.temperature <= 2:
            raise ValueError("AIDA_COPILOT_TEMPERATURE must be between 0 and 2")
        if self.max_context_records <= 0:
            raise ValueError("AIDA_COPILOT_MAX_CONTEXT_RECORDS must be positive")
        if self.fallback != "rule_based":
            raise ValueError("AIDA_COPILOT_FALLBACK currently supports only rule_based")
