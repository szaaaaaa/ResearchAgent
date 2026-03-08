from __future__ import annotations

import argparse

from src.agent.infra.search.sources import fetch_arxiv_records
from src.common.arg_utils import add_fetch_control_args, add_fetch_storage_args
from src.common.cli_utils import add_config_arg, parse_args_and_cfg, run_cli
from src.common.rag_config import (
    fetch_delay,
    fetch_download,
    fetch_max_results,
    ingest_latex_download_source,
    ingest_latex_source_dir,
    papers_dir,
    sqlite_path,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True, help="arXiv query string")
    add_config_arg(ap, __file__)
    add_fetch_storage_args(ap)
    add_fetch_control_args(ap)
    ap.add_argument("--print_limit", type=int, default=5, help="How many records to print")
    args, root, cfg = parse_args_and_cfg(ap, __file__)

    papers_dir_v = papers_dir(root, cfg, args.papers_dir)
    sqlite_path_v = sqlite_path(root, cfg, args.sqlite_path)
    max_results = fetch_max_results(cfg, args.max_results)
    polite_delay_sec = fetch_delay(cfg, args.polite_delay_sec)
    download = fetch_download(cfg, args.download)
    download_source = ingest_latex_download_source(cfg)
    source_dir = ingest_latex_source_dir(root, cfg)

    print(">> fetch_arxiv start")
    print(f">> query = {args.query}")
    print(f">> sqlite_path = {sqlite_path_v}")
    print(f">> papers_dir = {papers_dir_v}")
    print(f">> max_results = {max_results}")
    print(f">> download = {download}")
    print(f">> polite_delay_sec = {polite_delay_sec}")

    records = fetch_arxiv_records(
        query=args.query,
        sqlite_path=str(sqlite_path_v),
        papers_dir=str(papers_dir_v),
        max_results=max_results,
        download=download,
        download_source=download_source,
        source_dir=str(source_dir),
        polite_delay_sec=polite_delay_sec,
    )

    n = len(records)
    print(f">> fetched records = {n}")
    for i, r in enumerate(records[: max(0, args.print_limit)], start=1):
        title = " ".join((r.title or "").split())
        if len(title) > 100:
            title = title[:100] + "..."
        print(f"[{i}] {r.uid} | year={r.year} | {title}")

    print("[OK] fetch_arxiv done")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli("fetch_arxiv", main))
