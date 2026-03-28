from __future__ import annotations

from pathlib import Path

import yaml


def load_custom_skill_additions(cwd: Path) -> dict[str, list[str]]:
    """从 <cwd>/skills/skills_config.yaml 加载角色到技能的附加映射。"""
    config_path = cwd / "skills" / "skills_config.yaml"
    if not config_path.is_file():
        return {}
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    additions = raw.get("role_skill_additions")
    if not isinstance(additions, dict):
        return {}
    result: dict[str, list[str]] = {}
    for role_id, skills in additions.items():
        if isinstance(skills, list):
            result[str(role_id)] = [str(s) for s in skills]
    return result
