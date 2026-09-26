import datetime as dt

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from kestrel.profile import DEMO_PROFILE
from kestrel.server import create_app

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>kestrel</title>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(dist):
    return TestClient(create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=dist))


def test_every_route_is_read_only(dist):
    app = create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=dist)
    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    assert routes, "expected API routes"
    for route in routes:
        assert route.methods <= {"GET", "HEAD"}, f"{route.path} allows {route.methods}"


def test_writes_are_refused(client):
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/api/home").status_code == 405


def test_health_shell_and_home(client):
    assert client.get("/api/health").json()["ok"] is True
    shell = client.get("/api/shell").json()
    assert shell["name"] == "Alex" and shell["app"]["accent"] == "rufous"
    assert shell["counts"] == {"accounts": 4, "books": 5, "strategies": 4}
    home = client.get("/api/home").json()
    assert home["summary"]["needs_you"] == 2
    assert home["net_worth"]["total"] > 0


def test_the_shell_never_exposes_source_settings(client, tmp_path):
    body = client.get("/api/shell").text
    assert "stale_after" not in body and "token_env" not in body


def test_an_unknown_api_path_is_a_json_404(client):
    response = client.get("/api/nope")
    assert response.status_code == 404 and "no such endpoint" in response.json()["detail"]


def test_pages_fall_back_to_the_app_and_files_are_served(client):
    assert "<title>kestrel</title>" in client.get("/strategies").text
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/favicon.svg").text == "<svg></svg>"


def test_a_path_outside_the_build_is_never_served(client):
    response = client.get("/..%2F..%2Fpyproject.toml")
    assert "[project]" not in response.text


def test_the_api_works_without_a_built_front_end():
    client = TestClient(create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=None))
    assert client.get("/api/health").status_code == 200
    assert client.get("/").status_code == 404
