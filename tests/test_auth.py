"""Shared-passphrase access control: nothing under /api serves before sign-in,
and with no passphrase configured nothing changes."""

from __future__ import annotations

import pytest

from server import config
from tests.conftest import make_reference, upload_reference


@pytest.fixture
def passphrase(monkeypatch) -> str:
    monkeypatch.setattr(config, "PASSPHRASE", "shimmy shimmy")
    return "shimmy shimmy"


def test_no_passphrase_means_no_sign_in(client):
    assert client.get("/api/references").status_code == 200
    assert client.get("/api/session").json() == {"signed_in": True}


def test_api_rejects_before_sign_in(client, passphrase):
    assert client.get("/api/references").status_code == 401
    assert client.get("/api/references/abc/media").status_code == 401
    assert client.head("/api/clips/abc/synced").status_code == 401
    assert client.get("/openapi.json").status_code == 401
    assert client.get("/api/session").json() == {"signed_in": False}


def test_wrong_passphrase_is_rejected(client, passphrase):
    resp = client.post("/api/session", json={"passphrase": "cha cha"})

    assert resp.status_code == 401
    assert "dancesync_session" not in resp.cookies
    assert client.get("/api/references").status_code == 401


def test_sign_in_lets_media_through(client, passphrase):
    resp = client.post("/api/session", json={"passphrase": passphrase})
    assert resp.status_code == 204
    assert "httponly" in resp.headers["set-cookie"].lower()

    reference = upload_reference(client, make_reference(duration_sec=10.0, seed=3))
    media = client.get(
        f"/api/references/{reference['id']}/media", headers={"Range": "bytes=0-99"}
    )
    assert media.status_code == 206
    assert client.get("/api/session").json() == {"signed_in": True}


def test_changing_the_passphrase_signs_everyone_out(client, passphrase, monkeypatch):
    client.post("/api/session", json={"passphrase": passphrase})
    monkeypatch.setattr(config, "PASSPHRASE", "new moves")

    assert client.get("/api/references").status_code == 401
