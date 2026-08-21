#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.copilot_config import CopilotConfig  # noqa: E402
from app.copilot_provider import (  # noqa: E402
    CopilotGenerationRequest,
    CopilotProviderError,
    OllamaCopilotProvider,
)


def main() -> None:
    config = CopilotConfig.from_env()
    if not config.enabled:
        raise SystemExit("Copilot smoke skipped: set AIDA_COPILOT_ENABLED=true.")
    if not config.api_key:
        raise SystemExit("Copilot smoke skipped: AIDA_COPILOT_API_KEY is not configured.")
    if config.provider != "ollama":
        raise SystemExit("Copilot smoke currently supports the Ollama provider.")

    provider = OllamaCopilotProvider(config)
    try:
        provider.validate_configured_model()
        result = provider.generate(
            CopilotGenerationRequest(
                system_prompt=(
                    "This is a connectivity smoke test. Return a short advisory-only "
                    "confirmation and do not claim any operational action was executed."
                ),
                user_prompt="Confirm that the configured Copilot model is reachable.",
            )
        )
    except CopilotProviderError as exc:
        raise SystemExit(f"Copilot smoke failed: {exc.reason}.") from exc

    print(
        f"Copilot smoke passed: provider={result.provider} model={result.model} "
        f"response_chars={len(result.answer)}"
    )


if __name__ == "__main__":
    main()
