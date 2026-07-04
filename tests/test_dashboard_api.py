from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

import dashboard.server as server_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    monkeypatch.setenv("NAC_PROVIDER_OVERRIDE", "mock")
    (tmp_path / ".nac-root").write_text("")
    server_module._studio = None
    server_module._PROVIDER_OVERRIDE = "mock"
    yield TestClient(server_module.app)
    server_module._studio = None


def test_list_projects_empty(client):
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_and_list_project(client):
    resp = client.post("/api/projects", json={"idea_text": "A temple in the clouds", "target_runtime_minutes": 20})
    assert resp.status_code == 200
    project_id = resp.json()["id"]

    resp = client.get("/api/projects")
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == project_id


def test_create_project_requires_idea(client):
    resp = client.post("/api/projects", json={})
    assert resp.status_code == 422


def test_status_unknown_project_404(client):
    resp = client.get("/api/projects/does-not-exist/status")
    assert resp.status_code == 404


def test_full_stage_pipeline_via_api(client):
    project_id = client.post("/api/projects", json={"idea_text": "An idea"}).json()["id"]

    for stage in ("story", "screenplay", "audio", "prompt"):
        resp = client.post(f"/api/projects/{project_id}/generate/{stage}")
        assert resp.status_code == 200, resp.text

    status = client.get(f"/api/projects/{project_id}/status").json()
    assert status["story_bible"] is True
    assert status["screenplay"] is True
    assert status["audio"] is True
    assert status["motion_poster_prompt"] is True

    content = client.get(f"/api/projects/{project_id}/content").json()
    assert content["story"]
    assert content["screenplay"]
    assert content["prompt"]


def test_generate_unknown_stage_422(client):
    project_id = client.post("/api/projects", json={"idea_text": "An idea"}).json()["id"]
    resp = client.post(f"/api/projects/{project_id}/generate/nonexistent")
    assert resp.status_code == 422


def test_review_workflow(client):
    project_id = client.post("/api/projects", json={"idea_text": "An idea"}).json()["id"]
    client.post(f"/api/projects/{project_id}/generate/story")

    resp = client.post(
        f"/api/projects/{project_id}/review",
        json={"stage": "story", "verdict": "approved", "comment": "looks good"},
    )
    assert resp.status_code == 200

    reviews = client.get(f"/api/projects/{project_id}/reviews").json()
    assert len(reviews) == 1
    assert reviews[0]["verdict"] == "approved"


def test_import_asset(client, tmp_path):
    project_id = client.post("/api/projects", json={"idea_text": "An idea"}).json()["id"]
    fake_file = tmp_path / "poster.png"
    fake_file.write_bytes(b"fake-bytes")

    with open(fake_file, "rb") as f:
        resp = client.post(
            f"/api/projects/{project_id}/import?capability=motion_poster",
            files={"file": ("poster.png", f, "image/png")},
        )
    assert resp.status_code == 200
    assert resp.json()["asset_id"]

    assets = client.get(f"/api/projects/{project_id}/assets").json()
    assert len(assets) == 1


def test_export_after_partial_pipeline(client):
    project_id = client.post("/api/projects", json={"idea_text": "An idea"}).json()["id"]
    client.post(f"/api/projects/{project_id}/generate/story")

    resp = client.post(f"/api/projects/{project_id}/export", json={})
    assert resp.status_code == 200
    assert resp.json()["path"]


def test_audio_route_404_before_generation(client):
    project_id = client.post("/api/projects", json={"idea_text": "An idea"}).json()["id"]
    resp = client.get(f"/api/projects/{project_id}/audio")
    assert resp.status_code == 404


def test_capabilities_and_provider_routes(client):
    resp = client.get("/api/capabilities")
    assert resp.status_code == 200
    assert any(c["capability"] == "screenplay" for c in resp.json())

    resp = client.get("/api/provider")
    assert resp.status_code == 200
    assert resp.json()["llm_provider"] == "MockProvider"


def test_demo_project_route(client):
    resp = client.post("/api/projects/demo")
    assert resp.status_code == 200
    project_id = resp.json()["id"]

    status = client.get(f"/api/projects/{project_id}/status").json()
    assert status["story_bible"] is True
    assert status["screenplay"] is True

    content = client.get(f"/api/projects/{project_id}/content").json()
    assert "Temple of Varuna" in content["story"]


def test_diagnostics_route(client):
    resp = client.get("/api/diagnostics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sqlite"] == "ok"
    assert body["provider"]["llm_provider"] == "MockProvider"
    assert isinstance(body["capabilities"], list)
    # Expanded diagnostics checks
    assert "storage" in body
    assert "snapshots_info" in body
    assert "graph_health" in body


def test_metrics_route(client):
    project_id = client.post("/api/projects", json={"idea_text": "An idea"}).json()["id"]
    client.post(f"/api/projects/{project_id}/generate/story")

    resp = client.get(f"/api/projects/{project_id}/metrics")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# --- STORAGE WORKSPACE TESTS ---

def test_storage_providers_endpoints(client):
    resp = client.get("/api/storage/providers")
    assert resp.status_code == 200
    providers = resp.json()
    assert len(providers) == 4
    names = [p["name"] for p in providers]
    assert "local" in names
    assert "external" in names
    assert "azure" in names
    assert "google" in names

    resp = client.get("/api/storage/active")
    assert resp.status_code == 200
    assert resp.json()["name"] == "local"


# --- SNAPSHOTS WORKSPACE TESTS ---

def test_snapshots_workflow_api(client):
    project_id = client.post("/api/projects", json={"idea_text": "A snapshot idea"}).json()["id"]
    client.post(f"/api/projects/{project_id}/generate/story")

    # 1. Create snapshot
    resp = client.post(f"/api/projects/{project_id}/snapshots")
    assert resp.status_code == 200
    snap = resp.json()
    snapshot_id = snap["manifest"]["snapshot_id"]
    assert snapshot_id
    assert snap["story"]["idea_text"] == "A snapshot idea"

    # 2. List snapshots
    resp = client.get("/api/snapshots")
    assert resp.status_code == 200
    snaps_list = resp.json()
    assert len(snaps_list) >= 1
    assert any(s["snapshot_id"] == snapshot_id for s in snaps_list)

    # 3. Inspect snapshot
    resp = client.get(f"/api/snapshots/{snapshot_id}")
    assert resp.status_code == 200
    assert resp.json()["manifest"]["snapshot_id"] == snapshot_id

    # 4. Verify snapshot
    resp = client.post(f"/api/snapshots/{snapshot_id}/verify")
    assert resp.status_code == 200
    assert resp.json()["verified"] is True
    assert resp.json()["violations"] == []

    # 5. Diff snapshots (requires creating a second snapshot)
    client.post(f"/api/projects/{project_id}/generate/screenplay")
    snap2 = client.post(f"/api/projects/{project_id}/snapshots").json()
    snapshot2_id = snap2["manifest"]["snapshot_id"]

    resp = client.post("/api/snapshots/diff", json={"snapshot1_id": snapshot_id, "snapshot2_id": snapshot2_id})
    assert resp.status_code == 200
    diff = resp.json()
    assert diff["project_ids_match"] is True
    assert "screenplay" in diff["story"]["modified_fields"]


# --- PACKAGES WORKSPACE TESTS ---

def test_packages_workflow_api(client):
    project_id = client.post("/api/projects", json={"idea_text": "A package idea"}).json()["id"]
    
    # 1. Create package
    resp = client.post(f"/api/projects/{project_id}/packages")
    assert resp.status_code == 200
    pkg = resp.json()
    package_id = pkg["package_id"]
    assert package_id
    
    # 2. List packages
    resp = client.get("/api/packages")
    assert resp.status_code == 200
    packages_list = resp.json()
    assert len(packages_list) >= 1
    assert any(p["package_id"] == package_id for p in packages_list)
    
    # 3. Get package manifest
    resp = client.get(f"/api/packages/{package_id}/manifest")
    assert resp.status_code == 200
    assert resp.json()["project_id"] == project_id
    
    # 4. Get package contents
    resp = client.get(f"/api/packages/{package_id}/contents")
    assert resp.status_code == 200
    contents = resp.json()
    assert len(contents["files"]) >= 3  # manifest.json, knowledge_graph.json, references.json, etc.
    paths = [f["path"] for f in contents["files"]]
    assert "manifest.json" in paths
    assert "graphs/knowledge_graph.json" in paths

