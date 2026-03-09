from __future__ import annotations

from src.agent.plugins.llm import openrouter_chat  # noqa: F401
from src.agent.plugins.registry import get_llm_backend
from src.agent.providers.llm_adapter import (
    ModelRequest,
    ModelResponse,
    coerce_structured_output,
    estimate_token_count,
    parse_structured_output,
    register_llm_provider,
)


class OpenRouterProvider:
    _backend_name = "openrouter_chat"

    def generate(self, request: ModelRequest) -> ModelResponse:
        backend = get_llm_backend(self._backend_name)
        content = backend.generate(
            system_prompt=request.system_prompt,
            user_prompt=request.user_prompt,
            model=request.model,
            temperature=request.temperature,
            cfg=request.cfg,
        )
        prompt_tokens = estimate_token_count(request.system_prompt) + estimate_token_count(request.user_prompt)
        completion_tokens = estimate_token_count(content)
        return ModelResponse(
            content=content,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            model=request.model,
        )

    def generate_structured(self, request: ModelRequest, schema: type):
        response = self.generate(request)
        return coerce_structured_output(parse_structured_output(response.content), schema)


register_llm_provider("openrouter", OpenRouterProvider())
