from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .models import RepairRequest
from .optimizer import optimize_requirements


app = FastAPI(title="Failure Requirement Repair API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/repair/requirements")
def repair_requirements(req: RepairRequest) -> dict:
    try:
        result = optimize_requirements(req)
        return result.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
