from __future__ import annotations

import importlib
import sys
import types

__all__ = ["graph"]


def __getattr__(name: str):
    if name == "graph":
        try:
            module = importlib.import_module("src.agent.graph")
        except ModuleNotFoundError as exc:
            if exc.name not in {"langgraph", "langgraph.graph"}:
                raise

            module = types.ModuleType("src.agent.graph")

            def _missing_run_research(*args, **kwargs):
                raise ModuleNotFoundError("langgraph is required to run legacy graph mode")

            module.run_research = _missing_run_research
            sys.modules.setdefault("src.agent.graph", module)
        globals()[name] = module
        return module
    raise AttributeError(f"module 'src.agent' has no attribute {name!r}")
