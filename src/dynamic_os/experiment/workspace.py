"""实验工作区管理 - 初始化、快照、恢复、读写可变文件。"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

_BUILTIN_TEMPLATE_DIR: Path = Path(__file__).parent / "templates" / "default"


@dataclass(frozen=True)
class WorkspaceConfig:
    """声明实验工作区的结构与约束。"""

    template: str = "builtin"
    custom_path: str = ""
    mutable_files: list[str] = field(default_factory=list)
    entry_point: str = "train.py"
    eval_script: str = "evaluate.py"


def init_workspace(config: WorkspaceConfig, run_dir: str | Path) -> Path:
    """将工作区模板复制到 *run_dir*/experiment_workspace 并返回其路径。

    当 ``template="builtin"`` 时使用内置默认模板。
    当 ``template="custom"`` 时复制 *config.custom_path* 指定的目录；
    该目录必须存在且包含 *entry_point* 和 *eval_script*。
    """
    run_dir = Path(run_dir)
    dest = run_dir / "experiment_workspace"

    if config.template == "builtin":
        source = _BUILTIN_TEMPLATE_DIR
        if not source.is_dir():
            raise FileNotFoundError(
                f"Built-in template directory not found: {source}"
            )
        shutil.copytree(source, dest, dirs_exist_ok=True)
    elif config.template == "custom":
        source = Path(config.custom_path)
        if not source.is_dir():
            raise FileNotFoundError(
                f"Custom workspace path does not exist: {source}"
            )
        if not (source / config.entry_point).is_file():
            raise FileNotFoundError(
                f"Entry point '{config.entry_point}' not found in {source}"
            )
        if not (source / config.eval_script).is_file():
            raise FileNotFoundError(
                f"Eval script '{config.eval_script}' not found in {source}"
            )
        shutil.copytree(source, dest, dirs_exist_ok=True)
    else:
        raise ValueError(
            f"Unknown template type '{config.template}'; expected 'builtin' or 'custom'"
        )

    return dest


def read_mutable_files(
    workspace: Path, mutable_files: list[str]
) -> dict[str, str]:
    """返回 *workspace* 中每个可变文件的 ``{relative_path: content}`` 字典。

    不存在的文件以空字符串值包含在内。
    """
    result: dict[str, str] = {}
    for rel in mutable_files:
        fp = workspace / rel
        if fp.is_file():
            result[rel] = fp.read_text(encoding="utf-8")
        else:
            result[rel] = ""
    return result


def write_mutable_files(
    workspace: Path, changes: dict[str, str]
) -> None:
    """将 *changes* (``{relative_path: content}``) 写入 *workspace*。

    父目录不存在时会自动创建。
    """
    for rel, content in changes.items():
        fp = workspace / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")


def snapshot_mutable(
    workspace: Path, mutable_files: list[str]
) -> dict[str, str]:
    """捕获所有可变文件的当前状态作为保存点字典。"""
    return read_mutable_files(workspace, mutable_files)


def restore_snapshot(
    workspace: Path, snapshot: dict[str, str]
) -> None:
    """通过写回所有文件来恢复之前捕获的快照。"""
    write_mutable_files(workspace, snapshot)


def parse_workspace_config(raw: dict) -> WorkspaceConfig:
    """从原始字典（如实验计划 YAML）构建 :class:`WorkspaceConfig`。

    缺失的键使用 dataclass 默认值。
    """
    return WorkspaceConfig(
        template=raw.get("template", "builtin"),
        custom_path=raw.get("custom_path", ""),
        mutable_files=list(raw.get("mutable_files", [])),
        entry_point=raw.get("entry_point", "train.py"),
        eval_script=raw.get("eval_script", "evaluate.py"),
    )
