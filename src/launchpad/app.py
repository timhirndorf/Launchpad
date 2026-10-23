"""FastAPI app: JSON at /api/panels, the front end at /."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles

from launchpad.service import build_panels

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"

app = FastAPI(title="Launchpad")


@app.get("/api/panels")
async def panels() -> dict:
    # yfinance is blocking, so keep it off the event loop.
    return await run_in_threadpool(build_panels)


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


def main() -> None:
    uvicorn.run("launchpad.app:app", host="127.0.0.1", port=8000, reload=True)
