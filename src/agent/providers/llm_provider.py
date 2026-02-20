from __future__ import annotations

import logging
import time
from typing import Any, Dict

from src.agent.core.factories import create_llm_backend

logger = logging.getLogger(__name__)


def call_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    cfg: Dict[str, Any],
    model: str | None = None,
    temperature: float | None = None,
) -> str:
    """Provider gateway for LLM calls.

    Nodes should only call this function and never call SDKs directly.
    """
    llm_cfg = cfg.get("llm", {})
    provider_cfg = cfg.get("providers", {}).get("llm", {})

    resolved_model = str(
        model
        or llm_cfg.get("model")
        or provider_cfg.get("default_model")
        or "gpt-4.1-mini"
    )
    resolved_temperature = float(
        temperature
        if temperature is not None
        else llm_cfg.get("temperature", provider_cfg.get("default_temperature", 0.3))
    )

    retries = int(provider_cfg.get("retries", 0))
    backoff_sec = float(provider_cfg.get("retry_backoff_sec", 1.0))
    backend_name = str(provider_cfg.get("backend", "openai_chat")).strip().lower()
    backend = create_llm_backend(cfg)

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return backend.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=resolved_model,
                temperature=resolved_temperature,
                cfg=cfg,
            )
        except Exception as exc:  # pragma: no cover - network path
            last_err = exc
            if attempt >= retries:
                break
            delay = max(0.0, backoff_sec) * (attempt + 1)
            logger.warning(
                "LLM backend '%s' failed (attempt %d/%d): %s; retry in %.1fs",
                backend_name,
                attempt + 1,
                retries + 1,
                exc,
                delay,
            )
            if delay > 0:
                time.sleep(delay)

    assert last_err is not None
    raise last_err

