import datetime as dt
import pathlib

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from kestrel.profile import DEMO_PROFILE
from kestrel.server import create_app

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
BASE_URL = "http://127.0.0.1"  # the Host the server allows; TestClient's default "testserver" is refused


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>kestrel</title>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(dist):
    return TestClient(create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=dist), base_url=BASE_URL)


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


def test_a_path_outside_the_build_is_never_served(tmp_path):
    base = tmp_path / "base"
    dist = base / "web" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>kestrel</title>", encoding="utf-8")
    (base / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    client = TestClient(create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=dist), base_url=BASE_URL)
    for path in ("/../../pyproject.toml", "/..%2F..%2Fpyproject.toml", "/assets/../../../pyproject.toml"):
        response = client.get(path)
        assert "[project]" not in response.text, path


def test_a_windows_network_path_is_refused_before_touching_the_filesystem(client, monkeypatch):
    touched: list[str] = []
    real_resolve, real_is_file = pathlib.Path.resolve, pathlib.Path.is_file

    def unc(path: pathlib.Path) -> bool:
        return str(path).startswith(("\\\\", "//"))

    # record, then delegate, except for a network path: even a regressed build must not reach the network here
    def resolve(self, *args, **kwargs):
        touched.append(str(self))
        return self if unc(self) else real_resolve(self, *args, **kwargs)

    def is_file(self, *args, **kwargs):
        touched.append(str(self))
        return False if unc(self) else real_is_file(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "resolve", resolve)
    monkeypatch.setattr(pathlib.Path, "is_file", is_file)
    response = client.get("/%5C%5Chost%5Cshare%5Cx.txt")
    assert response.status_code == 200 and "<title>kestrel</title>" in response.text
    assert not [t for t in touched if t.startswith(("\\\\", "//"))], touched


def test_a_request_for_another_host_is_refused(client):
    """DNS rebinding: a page on another site that resolves its name to 127.0.0.1 still sends its own Host."""
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
    assert client.get("/api/health", headers={"Host": "localhost:8030"}).status_code == 200


def test_the_api_works_without_a_built_front_end():
    client = TestClient(create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=None), base_url=BASE_URL)
    assert client.get("/api/health").status_code == 200
    assert client.get("/").status_code == 404


def test_a_nul_character_in_a_path_gets_the_app_not_an_error(client):
    response = client.get("/strategies%00x")
    assert response.status_code == 200 and "<title>kestrel</title>" in response.text
