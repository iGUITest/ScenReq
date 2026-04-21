from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .word_json_sync import SyncResult, sync_word_to_json


app = FastAPI(title="Manual Edit Sync API", version="0.1.0")

# In-memory watcher registry for standalone mode.
_watch_tasks: Dict[str, asyncio.Task] = {}


class SyncRequest(BaseModel):
    report_path: str = Field(..., description="Path of the edited .docx report")
    srs_json_path: Optional[str] = Field(None, description="Optional SRS json path")
    tests_json_path: Optional[str] = Field(None, description="Optional test requirements json path")


class WatchRequest(SyncRequest):
    poll_interval_seconds: float = Field(2.0, ge=0.5, le=30.0)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/manual-edit/sync")
def manual_sync(req: SyncRequest) -> dict:
    try:
        result: SyncResult = sync_word_to_json(
            report_path=req.report_path,
            srs_json_path=req.srs_json_path,
            tests_json_path=req.tests_json_path,
        )
        payload = asdict(result)
        payload["ok"] = True
        return payload
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _watch_loop(req: WatchRequest) -> None:
    import os

    report_path = req.report_path
    last_mtime = os.path.getmtime(report_path)

    while True:
        await asyncio.sleep(req.poll_interval_seconds)
        try:
            new_mtime = os.path.getmtime(report_path)
            if new_mtime > last_mtime:
                sync_word_to_json(
                    report_path=req.report_path,
                    srs_json_path=req.srs_json_path,
                    tests_json_path=req.tests_json_path,
                )
                last_mtime = new_mtime
        except FileNotFoundError:
            # Keep waiting for the file if it is temporarily unavailable.
            continue


@app.post("/api/manual-edit/watch/start")
async def start_watch(req: WatchRequest) -> dict:
    task_key = req.report_path
    if task_key in _watch_tasks and not _watch_tasks[task_key].done():
        return {"ok": True, "message": "Watcher already running", "report_path": req.report_path}

    task = asyncio.create_task(_watch_loop(req))
    _watch_tasks[task_key] = task
    return {"ok": True, "message": "Watcher started", "report_path": req.report_path}


@app.post("/api/manual-edit/watch/stop")
async def stop_watch(req: SyncRequest) -> dict:
    task_key = req.report_path
    task = _watch_tasks.get(task_key)
    if not task:
        return {"ok": True, "message": "Watcher not found", "report_path": req.report_path}

    task.cancel()
    return {"ok": True, "message": "Watcher stopped", "report_path": req.report_path}
