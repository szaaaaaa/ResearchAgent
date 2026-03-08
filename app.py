import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "agent.yaml"
ENV_PATH = ROOT / ".env"
FRONTEND_DIST = ROOT / "frontend" / "dist"
CREDENTIAL_KEYS = (
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "SERPAPI_API_KEY",
    "GOOGLE_CSE_API_KEY",
    "GOOGLE_CSE_CX",
    "BING_API_KEY",
    "GITHUB_TOKEN",
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/config")
def get_config():
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


@app.post("/api/config")
async def save_config(request: Request):
    new_config = await request.json()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        yaml.safe_dump(new_config, file, allow_unicode=True, sort_keys=False)
    return {"status": "success"}


def _read_env_file() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _write_env_file(values: dict[str, str]) -> None:
    ENV_PATH.write_text(
        "".join(f'{key}="{value}"\n' for key, value in values.items()),
        encoding="utf-8",
    )


@app.get("/api/credentials")
def get_credentials():
    env_values = _read_env_file()
    return {key: env_values.get(key, "") for key in CREDENTIAL_KEYS}


@app.post("/api/credentials")
async def save_credentials(request: Request):
    payload = await request.json()
    existing = _read_env_file()
    for key in CREDENTIAL_KEYS:
        value = payload.get(key, "")
        existing[key] = "" if value is None else str(value)
    _write_env_file(existing)
    return {"status": "success"}


def _build_run_command(payload: dict[str, Any]) -> list[str]:
    run_overrides = payload.get("runOverrides", payload)
    topic = str(run_overrides.get("topic", "") or "").strip()
    resume_run_id = str(run_overrides.get("resume_run_id", "") or "").strip()

    if not topic and not resume_run_id:
        raise HTTPException(status_code=400, detail="topic or resume_run_id is required")

    command = [sys.executable, "-u", "scripts/run_agent.py"]

    if topic:
        command.extend(["--topic", topic])
    if resume_run_id:
        command.extend(["--resume-run-id", resume_run_id])

    option_map = {
        "output_dir": "--output_dir",
        "language": "--language",
        "model": "--model",
        "max_iter": "--max_iter",
        "papers_per_query": "--papers_per_query",
    }
    for key, flag in option_map.items():
        value = run_overrides.get(key)
        if value not in (None, ""):
            command.extend([flag, str(value)])

    sources = run_overrides.get("sources")
    if isinstance(sources, list) and sources:
        selected = [str(item).strip() for item in sources if str(item).strip()]
        if selected:
            command.extend(["--sources", ",".join(selected)])

    if bool(run_overrides.get("no_web", False)):
        command.append("--no-web")
    if bool(run_overrides.get("no_scrape", False)):
        command.append("--no-scrape")
    if bool(run_overrides.get("verbose", False)):
        command.append("--verbose")

    mode = str(run_overrides.get("mode", "") or "os").strip().lower()
    if mode:
        command.extend(["--mode", mode])

    return command


@app.post("/api/run")
async def run_agent(request: Request):
    payload = await request.json()
    command = _build_run_command(payload)
    request_credentials = payload.get("credentials", {})
    saved_credentials = _read_env_file()
    env = os.environ.copy()
    env.update(saved_credentials)
    if isinstance(request_credentials, dict):
        env.update(
            {
                key: str(value)
                for key, value in request_credentials.items()
                if key in CREDENTIAL_KEYS and str(value).strip()
            }
        )

    def generate_output():
        process = None
        try:
            process = subprocess.Popen(
                command,
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            if process.stdout is not None:
                for line in process.stdout:
                    yield line
            exit_code = process.wait()
            if exit_code != 0:
                yield f"\n[run_agent exited with code {exit_code}]\n"
        except Exception as exc:
            yield f"\n[api run error] {exc}\n"
        finally:
            if process is not None and process.stdout is not None:
                process.stdout.close()
            if process is not None and process.poll() is None:
                process.wait()

    return StreamingResponse(generate_output(), media_type="text/plain")


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
