"""Sprint 2A Director Studio server. Every route is a thin wrapper over
`nac.Studio` - no business logic here. `from nac import Studio` is the only NAC
import in this file, matching the CLI/Agent-OS-bridge boundary discipline.

STOP-CONDITION NOTE (Sprint 2A spec): fields the spec asked for that have no
backend support - Project Name, Genre, Language, Audience, Output Type, Target
Platforms, Aspect Ratios, Quality Target, Execution Mode, GPU usage, Credits,
non-registered providers (Gemma/Llama/Kokoro/XTTS/Higgsfield/Runway/...), Shorts
as independent output nodes - are NOT implemented here. See
wiki/nac-next-steps.md / the Sprint 2A report for the full list. Inventing fake
persistence for them was explicitly out of scope per the spec's own rule.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from nac import Studio

_PROVIDER_OVERRIDE = os.environ.get("NAC_PROVIDER_OVERRIDE")  # "mock" for tests
_studio: Studio | None = None


def get_studio() -> Studio:
    global _studio
    if _studio is None:
        _studio = Studio(provider_override=_PROVIDER_OVERRIDE)
    return _studio


app = FastAPI(title="NAC Director Studio")


@app.exception_handler(requests.exceptions.HTTPError)
async def llm_provider_error_handler(request: Request, exc: requests.exceptions.HTTPError):
    """Provider failures (e.g. OpenRouter free-tier 429 rate limits) previously
    propagated as a bare, unhandled 500 with no message - indistinguishable in the
    UI from a real click/JS bug. Surface the actual cause instead."""
    status = exc.response.status_code if exc.response is not None else 502
    if status == 429:
        detail = "The LLM provider rate-limited this request (HTTP 429 - too many requests, likely the OpenRouter free tier). Wait a moment and try again, or switch provider."
    else:
        detail = f"The LLM provider returned an error: {exc}"
    return JSONResponse(status_code=502, content={"detail": detail})

_STATIC_DIR = Path(__file__).parent / "static"


@app.get("/api/projects")
def list_projects():
    return get_studio().list_projects()


@app.post("/api/projects")
def create_project(body: dict):
    idea_text = body.get("idea_text")
    if not idea_text:
        raise HTTPException(422, "idea_text is required")
    target_runtime_minutes = int(body.get("target_runtime_minutes", 15))
    project_id = get_studio().create_project(idea_text, target_runtime_minutes=target_runtime_minutes)
    return {"id": project_id}


@app.get("/api/projects/{project_id}/status")
def get_status(project_id: str):
    try:
        return get_studio().get_status(project_id)
    except KeyError:
        raise HTTPException(404, f"No project {project_id}")


@app.get("/api/projects/{project_id}/content")
def get_content(project_id: str):
    try:
        return get_studio().get_stage_content(project_id)
    except KeyError:
        raise HTTPException(404, f"No project {project_id}")


@app.get("/api/projects/{project_id}/reviews")
def get_reviews(project_id: str):
    return get_studio().get_reviews(project_id)


@app.get("/api/projects/{project_id}/assets")
def get_assets(project_id: str):
    return get_studio().get_assets(project_id)


@app.get("/api/projects/{project_id}/metrics")
def get_metrics(project_id: str):
    return get_studio().get_metrics(project_id)


@app.get("/api/capabilities")
def get_capabilities():
    return get_studio().get_capabilities()


@app.get("/api/provider")
def get_provider():
    return get_studio().get_provider_info()


@app.get("/api/diagnostics")
def get_diagnostics():
    return get_studio().get_diagnostics()


_VALID_STAGES = ("story", "screenplay", "audio", "prompt")


@app.post("/api/projects/{project_id}/generate/{stage}")
def generate_stage(project_id: str, stage: str):
    if stage not in _VALID_STAGES:
        raise HTTPException(422, f"Unknown stage '{stage}'. Valid: {_VALID_STAGES}")
    try:
        result = get_studio().regenerate_stage(project_id, stage)
    except KeyError:
        raise HTTPException(404, f"No project {project_id}")
    return {"stage": stage, "result": str(result)}


@app.post("/api/projects/{project_id}/review")
def record_review(project_id: str, body: dict):
    stage = body.get("stage")
    verdict = body.get("verdict")
    if not stage or not verdict:
        raise HTTPException(422, "stage and verdict are required")
    get_studio().record_review(project_id, stage, verdict, comment=body.get("comment"))
    return {"ok": True}


@app.post("/api/projects/{project_id}/import")
async def import_asset(project_id: str, capability: str, file: UploadFile):
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or "asset").suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        asset_id = get_studio().import_asset(project_id, capability, tmp_path)
    finally:
        os.unlink(tmp_path)
    return {"asset_id": asset_id}


@app.post("/api/projects/{project_id}/export")
def export_project_route(project_id: str, body: dict):
    out_dir = body.get("out_dir") or f"projects/{project_id}_package"
    try:
        path = get_studio().export(project_id, Path(out_dir))
    except KeyError:
        raise HTTPException(404, f"No project {project_id}")
    return {"path": str(path)}


@app.get("/api/projects/{project_id}/audio")
def get_audio(project_id: str):
    try:
        audio_path = get_studio().get_audio_path(project_id)
    except KeyError:
        raise HTTPException(404, f"No project {project_id}")
    if not audio_path or not audio_path.is_file():
        raise HTTPException(404, "No audio generated for this project yet")
    return FileResponse(str(audio_path), media_type="audio/wav")


if _STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
