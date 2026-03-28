from __future__ import annotations

import ast

import yaml

from src.dynamic_os.contracts.skill_spec import SkillSpec


def validate_skill_source(source: str) -> list[str]:
    """Validate generated skill source code. Returns list of errors (empty if valid)."""
    errors: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        errors.append(f"Syntax error: {exc}")
        return errors

    has_run = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run":
            has_run = True
            if len(node.args.args) < 1:
                errors.append("run() must accept at least one argument (ctx)")
    if not has_run:
        errors.append("Missing 'async def run(ctx)' function")
    return errors


def validate_skill_yaml(yaml_content: str) -> tuple[SkillSpec | None, list[str]]:
    """Validate generated skill.yaml content. Returns (spec, errors)."""
    errors: list[str] = []
    try:
        data = yaml.safe_load(yaml_content)
        spec = SkillSpec.model_validate(data)
        return spec, []
    except Exception as exc:
        errors.append(str(exc))
        return None, errors
