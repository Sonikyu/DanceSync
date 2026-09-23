"""The built web app is served from the API's origin, behind the API routes."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.web import mount_web_app


def _app_with_build(dist_dir) -> TestClient:
    app = FastAPI()

    @app.get("/api/ping")
    def ping() -> dict:
        return {"ok": True}

    mount_web_app(app, dist_dir)
    return TestClient(app)


def _write_build(dist_dir) -> None:
    (dist_dir / "assets").mkdir(parents=True)
    (dist_dir / "index.html").write_text("<div id=root></div>")
    (dist_dir / "assets" / "app.js").write_text("console.log(1)")


def test_serves_index_and_assets(tmp_path):
    _write_build(tmp_path)
    client = _app_with_build(tmp_path)

    assert client.get("/").text == "<div id=root></div>"
    assert client.get("/assets/app.js").text == "console.log(1)"


def test_api_routes_win(tmp_path):
    _write_build(tmp_path)
    client = _app_with_build(tmp_path)

    assert client.get("/api/ping").json() == {"ok": True}
    assert client.get("/api/nope").status_code == 404


def test_deep_link_gets_index(tmp_path):
    _write_build(tmp_path)
    client = _app_with_build(tmp_path)

    resp = client.get("/watch/some-clip")
    assert resp.status_code == 200
    assert resp.text == "<div id=root></div>"


def test_missing_asset_is_404(tmp_path):
    _write_build(tmp_path)
    client = _app_with_build(tmp_path)

    assert client.get("/assets/stale.js").status_code == 404


def test_no_escape_from_build_dir(tmp_path):
    dist_dir = tmp_path / "dist"
    _write_build(dist_dir)
    (tmp_path / "secret.txt").write_text("nope")
    client = _app_with_build(dist_dir)

    assert "nope" not in client.get("/../secret.txt").text
    assert "nope" not in client.get("/%2e%2e/secret.txt").text


def test_no_build_mounts_nothing(tmp_path):
    client = _app_with_build(tmp_path / "missing")

    assert client.get("/").status_code == 404
