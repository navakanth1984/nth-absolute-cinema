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


def test_diagnostics_route(client):
    resp = client.get("/api/diagnostics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sqlite"] == "ok"
    assert body["provider"]["llm_provider"] == "MockProvider"
    assert isinstance(body["capabilities"], list)


def test_metrics_route(client):
    project_id = client.post("/api/projects", json={"idea_text": "An idea"}).json()["id"]
    client.post(f"/api/projects/{project_id}/generate/story")

    resp = client.get(f"/api/projects/{project_id}/metrics")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
