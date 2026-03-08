from __future__ import annotations

import json
from dataclasses import dataclass, field, is_dataclass
from typing import Any, Protocol, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ModelRequest:
    system_prompt: str
    user_prompt: str
    model: str
    temperature: float
    max_tokens: int | None = None
    cfg: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    content: str
    usage: dict[str, Any] = field(default_factory=dict)
    model: str = ""


class LLMProvider(Protocol):
    def generate(self, request: ModelRequest) -> ModelResponse:
        ...

    def generate_structured(self, request: ModelRequest, schema: type[T]) -> T:
        ...


def estimate_token_count(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / 4))


def parse_structured_output(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


def coerce_structured_output(data: Any, schema: type[T]) -> T:
    if schema is dict:
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict structured output, got {type(data).__name__}")
        return data

    if hasattr(schema, "model_validate"):
        return schema.model_validate(data)

    if hasattr(schema, "parse_obj"):
        return schema.parse_obj(data)

    if is_dataclass(schema):
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict structured output for {schema.__name__}")
        return schema(**data)

    try:
        if isinstance(data, schema):
            return data
    except TypeError:
        pass

    return schema(data)


_LLM_PROVIDERS: dict[str, LLMProvider] = {}


def register_llm_provider(name: str, provider: LLMProvider) -> None:
    key = str(name).strip().lower()
    if not key:
        raise ValueError("LLM provider name cannot be empty")
    _LLM_PROVIDERS[key] = provider


def get_llm_provider(name: str) -> LLMProvider:
    key = str(name).strip().lower()
    try:
        return _LLM_PROVIDERS[key]
    except KeyError as exc:
        supported = ", ".join(sorted(_LLM_PROVIDERS)) or "(none)"
        raise ValueError(f"Unknown LLM provider: {name}. Supported: {supported}") from exc
