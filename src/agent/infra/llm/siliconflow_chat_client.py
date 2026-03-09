from __future__ import annotations

import os
from typing import Any, Dict

from openai import OpenAI

DEFAULT_SILICONFLOW_BASE_URL = "https://api.siliconflow.com/v1"
DEFAULT_SILICONFLOW_API_KEY_ENV = "SILICONFLOW_API_KEY"


def generate_siliconflow_chat_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    cfg: Dict[str, Any] | None = None,
) -> str:
    provider_cfg = ((cfg or {}).get("providers") or {}).get("llm", {})
    key_env_name = str(
        provider_cfg.get("siliconflow_api_key_env", DEFAULT_SILICONFLOW_API_KEY_ENV)
    ).strip() or DEFAULT_SILICONFLOW_API_KEY_ENV
    api_key = os.environ.get(key_env_name)
    if not api_key:
        raise RuntimeError(f"Missing {key_env_name} in environment variables.")

    base_url = str(provider_cfg.get("siliconflow_base_url", DEFAULT_SILICONFLOW_BASE_URL)).strip()
    if not base_url:
        base_url = DEFAULT_SILICONFLOW_BASE_URL

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content or ""
