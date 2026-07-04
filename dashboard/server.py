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

import json
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


@app.post("/api/projects/demo")
def create_demo_project():
    project_id = get_studio().create_demo_project()
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


# --- STORAGE WORKSPACE API ---

@app.get("/api/storage/providers")
def list_storage_providers():
    return get_studio().list_storage_providers()

@app.get("/api/storage/active")
def get_active_storage_provider():
    return get_studio().get_active_storage_provider()


# --- SNAPSHOTS WORKSPACE API ---

def get_packages_dir() -> Path:
    resolver = get_studio()._resolver
    path = resolver.resolve("projects/storage/local/packages")
    path.mkdir(parents=True, exist_ok=True)
    return path

def snapshot_to_dict(snapshot: Any) -> dict:
    return {
        "manifest": {
            "project_id": snapshot.manifest.project_id,
            "snapshot_id": snapshot.manifest.snapshot_id,
            "data_hash": snapshot.manifest.data_hash,
            "component_hashes": snapshot.manifest.component_hashes,
            "engine_version": snapshot.manifest.engine_version,
            "sdk_version": snapshot.manifest.sdk_version,
            "graph_spec_version": snapshot.manifest.graph_spec_version,
            "genome_spec_version": snapshot.manifest.genome_spec_version,
            "created_at": snapshot.manifest.created_at,
            "compiler_versions": snapshot.manifest.compiler_versions,
            "pack_versions": snapshot.manifest.pack_versions,
            "provider_metadata": snapshot.manifest.provider_metadata,
            "environment_metadata": snapshot.manifest.environment_metadata,
            "runtime_config": snapshot.manifest.runtime_config,
        },
        "story": snapshot.story,
        "compiler_metrics": snapshot.compiler_metrics,
        "review_log": snapshot.review_log,
        "assets": snapshot.assets,
        "genomes": snapshot.genomes,
        "custom_metadata": snapshot.custom_metadata,
    }

@app.post("/api/projects/{project_id}/snapshots")
def create_snapshot(project_id: str):
    try:
        snapshot = get_studio().create_project_snapshot(project_id)
        # Automatically serialize to local storage directory to make it listable
        pkg_dir = get_packages_dir() / f"{snapshot.manifest.snapshot_id}.nac"
        get_studio().serialize_snapshot_to_nac(snapshot, pkg_dir)
        return snapshot_to_dict(snapshot)
    except KeyError:
        raise HTTPException(404, f"No project {project_id}")

@app.get("/api/snapshots")
def list_snapshots():
    pkg_dir = get_packages_dir()
    results = []
    for p in pkg_dir.iterdir():
        if p.is_dir() and (p / "manifest.json").is_file():
            try:
                manifest_data = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
                results.append({
                    "snapshot_id": manifest_data.get("snapshot_id"),
                    "project_id": manifest_data.get("project_id"),
                    "created_at": manifest_data.get("created_at"),
                    "data_hash": manifest_data.get("data_hash"),
                    "path": str(p),
                })
            except Exception:
                pass
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results

@app.get("/api/snapshots/{snapshot_id}")
def inspect_snapshot(snapshot_id: str):
    p = get_packages_dir() / f"{snapshot_id}.nac"
    if not p.is_dir():
        raise HTTPException(404, f"Snapshot {snapshot_id} not found")
    try:
        snapshot = get_studio().deserialize_nac_to_snapshot(p)
        return snapshot_to_dict(snapshot)
    except Exception as e:
        raise HTTPException(500, f"Failed to load snapshot: {e}")

@app.post("/api/snapshots/{snapshot_id}/verify")
def verify_snapshot_integrity(snapshot_id: str):
    p = get_packages_dir() / f"{snapshot_id}.nac"
    if not p.is_dir():
        raise HTTPException(404, f"Snapshot {snapshot_id} not found")
    try:
        snapshot = get_studio().deserialize_nac_to_snapshot(p)
        verified = get_studio().verify_project_snapshot(snapshot)
        violations = get_studio().validate_project_snapshot(snapshot)
        return {"snapshot_id": snapshot_id, "verified": verified, "violations": violations}
    except Exception as e:
        return {"snapshot_id": snapshot_id, "verified": False, "violations": [f"Load failure: {e}"]}

@app.post("/api/snapshots/diff")
def diff_snapshots_route(body: dict):
    snap1_id = body.get("snapshot1_id")
    snap2_id = body.get("snapshot2_id")
    if not snap1_id or not snap2_id:
        raise HTTPException(422, "snapshot1_id and snapshot2_id are required")
    
    p1 = get_packages_dir() / f"{snap1_id}.nac"
    p2 = get_packages_dir() / f"{snap2_id}.nac"
    
    if not p1.is_dir():
        raise HTTPException(404, f"Snapshot {snap1_id} not found")
    if not p2.is_dir():
        raise HTTPException(404, f"Snapshot {snap2_id} not found")
        
    try:
        s1 = get_studio().deserialize_nac_to_snapshot(p1)
        s2 = get_studio().deserialize_nac_to_snapshot(p2)
        diff = get_studio().diff_project_snapshots(s1, s2)
        return diff
    except Exception as e:
        raise HTTPException(500, f"Diff computation failed: {e}")


# --- PACKAGES WORKSPACE API ---

@app.post("/api/projects/{project_id}/packages")
def create_package(project_id: str):
    try:
        snapshot = get_studio().create_project_snapshot(project_id)
        pkg_dir = get_packages_dir() / f"{project_id}_{snapshot.manifest.snapshot_id}.nac"
        get_studio().serialize_snapshot_to_nac(snapshot, pkg_dir)
        return {
            "package_id": f"{project_id}_{snapshot.manifest.snapshot_id}.nac",
            "snapshot_id": snapshot.manifest.snapshot_id,
            "path": str(pkg_dir),
            "manifest": {
                "project_id": snapshot.manifest.project_id,
                "data_hash": snapshot.manifest.data_hash,
                "created_at": snapshot.manifest.created_at,
            }
        }
    except KeyError:
        raise HTTPException(404, f"No project {project_id}")

@app.get("/api/packages")
def list_packages():
    pkg_dir = get_packages_dir()
    results = []
    for p in pkg_dir.iterdir():
        if p.is_dir() and (p / "manifest.json").is_file():
            try:
                manifest_data = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
                results.append({
                    "package_id": p.name,
                    "project_id": manifest_data.get("project_id"),
                    "created_at": manifest_data.get("created_at"),
                    "data_hash": manifest_data.get("data_hash"),
                    "path": str(p),
                })
            except Exception:
                pass
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results

@app.get("/api/packages/{package_id}/manifest")
def get_package_manifest(package_id: str):
    p = get_packages_dir() / package_id
    if not p.is_dir():
        raise HTTPException(404, f"Package {package_id} not found")
    try:
        manifest_data = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
        return manifest_data
    except Exception as e:
        raise HTTPException(500, f"Failed to read manifest: {e}")

@app.get("/api/packages/{package_id}/contents")
def get_package_contents(package_id: str):
    p = get_packages_dir() / package_id
    if not p.is_dir():
        raise HTTPException(404, f"Package {package_id} not found")
        
    files = []
    for child in p.rglob("*"):
        if child.is_file():
            files.append({
                "path": child.relative_to(p).as_posix(),
                "size_bytes": child.stat().st_size,
            })
    return {"package_id": package_id, "files": sorted(files, key=lambda x: x["path"])}


if _STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
