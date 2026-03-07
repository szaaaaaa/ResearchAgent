from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Tuple

REDACTED = "***REDACTED***"

_SENSITIVE_KEY_TOKENS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "authorization",
    "access_key",
    "private_key",
    "client_secret",
)
_ALLOWED_CONFIG_KEY_SUFFIXES = (
    "_api_key_env",
    "_token_env",
    "_secret_env",
    "_password_env",
)
_LIKELY_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_\-\.=:/+]{8,}"),
)


def _normalized_key(key: Any) -> str:
    return str(key or "").strip().lower()


def _is_sensitive_key_name(key: Any) -> bool:
    normalized = _normalized_key(key)
    if not normalized:
        return False
    if normalized.endswith(_ALLOWED_CONFIG_KEY_SUFFIXES):
        return False
    return any(
        normalized == token
        or normalized.endswith(f"_{token}")
        or normalized.startswith(f"{token}_")
        for token in _SENSITIVE_KEY_TOKENS
    )


def _sensitive_env_values() -> List[str]:
    values: List[str] = []
    for env_name, env_value in os.environ.items():
        normalized = env_name.strip().lower()
        if not env_value:
            continue
        if any(token in normalized for token in _SENSITIVE_KEY_TOKENS):
            values.append(str(env_value))
    values.sort(key=len, reverse=True)
    return values


def redact_text(value: str) -> str:
    out = str(value)
    for secret in _sensitive_env_values():
        out = out.replace(secret, REDACTED)
    for pattern in _LIKELY_SECRET_PATTERNS:
        out = pattern.sub(REDACTED, out)
    return out


def redact_data(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: Dict[Any, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key_name(key):
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_data(item)
        return redacted
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_data(item) for item in value)
    if isinstance(value, str):
        return redact_text(value)
    return value


def find_inline_secret_paths(value: Any, path: Tuple[str, ...] = ()) -> List[str]:
    findings: List[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_str = str(key)
            child_path = path + (key_str,)
            if _is_sensitive_key_name(key):
                findings.append(".".join(child_path))
                continue
            findings.extend(find_inline_secret_paths(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(find_inline_secret_paths(item, path + (str(index),)))
    return findings


def assert_no_inline_secrets(cfg: Dict[str, Any]) -> None:
    findings = find_inline_secret_paths(cfg)
    if findings:
        raise ValueError(
            "Inline secrets are not allowed in config. Use environment variables instead. "
            f"Offending paths: {', '.join(sorted(findings))}"
        )


class RedactingLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(str(record.msg))
        if isinstance(record.args, dict):
            record.args = redact_data(record.args)
        elif isinstance(record.args, tuple):
            record.args = tuple(redact_data(arg) for arg in record.args)
        elif record.args:
            record.args = redact_data(record.args)
        return True


def install_logging_redaction() -> None:
    root = logging.getLogger()
    for handler in root.handlers:
        if any(isinstance(existing, RedactingLogFilter) for existing in handler.filters):
            continue
        handler.addFilter(RedactingLogFilter())
