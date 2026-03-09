from __future__ import annotations

from typing import Any, Dict

from src.agent.infra.llm.siliconflow_chat_client import generate_siliconflow_chat_completion
from src.agent.plugins.registry import register_llm_backend


class SiliconFlowChatBackend:
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        cfg: Dict[str, Any],
    ) -> str:
        return generate_siliconflow_chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            cfg=cfg,
        )


register_llm_backend("siliconflow_chat", SiliconFlowChatBackend())

