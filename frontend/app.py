import subprocess
import sys
from pathlib import Path

import uvicorn
import yaml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "agent.yaml"
FRONTEND_DIST = ROOT / "frontend" / "dist"

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


@app.post("/api/run")
async def run_agent(request: Request):
    data = await request.json()
    topic = str(data.get("topic", "")).strip()

    def generate_output():
        process = subprocess.Popen(
            [sys.executable, "scripts/run_agent.py", "--topic", topic],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        try:
            if process.stdout is not None:
                for line in process.stdout:
                    yield line
        finally:
            if process.stdout is not None:
                process.stdout.close()
            process.wait()

    return StreamingResponse(generate_output(), media_type="text/plain")


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
