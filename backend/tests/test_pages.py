"""The public pages rendered at build time are served at their paths, "/" included; without them, the app's shell.
The app's own pages get the shell; any other address is a 404, with the build's not-found page."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main
from app.main import app as api


@pytest.fixture
def site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(app.main, "FRONTEND_DIR", tmp_path)
    (tmp_path / "index.html").write_text("<html>shell</html>")
    return tmp_path


def test_prerendered_pages_are_served_at_their_paths(site: Path) -> None:
    (site / "check.html").write_text("<html>check page</html>")
    (site / "privacy.html").write_text("<html>privacy page</html>")
    client = TestClient(api)
    for path, body in (("/", "check page"), ("/check", "check page"), ("/privacy", "privacy page")):
        response = client.get(path, headers={"Accept": "*/*"})  # crawlers and curl get the page too
        assert (response.status_code, body in response.text) == (200, True), path
        assert response.headers["content-type"].startswith("text/html")
    assert client.head("/check").status_code == 200
    assert client.get("/terms").text == "<html>shell</html>"  # not rendered in this build: the app


@pytest.mark.usefixtures("site")
def test_pricing_opens_the_plans_on_the_check_page() -> None:
    client = TestClient(api, follow_redirects=False)
    response = client.get("/pricing", headers={"Accept": "text/html"})
    assert (response.status_code, response.headers["location"]) == (307, "/check#pricing")
    assert client.head("/pricing").status_code == 307


def test_without_a_build_the_pages_are_404(site: Path) -> None:
    (site / "index.html").unlink()
    assert TestClient(api).get("/check").status_code == 404


ROUTE_TREE = Path(__file__).parents[2] / "frontend" / "src" / "routeTree.gen.ts"


@pytest.mark.usefixtures("site")
def test_every_frontend_route_is_served() -> None:
    """A route added to the frontend needs its path in PRERENDERED or APP_PAGES, or a reload there would be a 404."""
    union = re.search(r"fullPaths:((?:\s*\|\s*'[^']*')+)", ROUTE_TREE.read_text())
    assert union, "no fullPaths in routeTree.gen.ts"
    paths = re.findall(r"'([^']*)'", union.group(1))
    assert "/login" in paths and "/ontario-pay-transparency-job-posting" in paths
    client = TestClient(api, follow_redirects=False)
    for path in paths:
        url = re.sub(r"\$\w+", "some-id", path.rstrip("/")) or "/"
        assert client.get(url, headers={"Accept": "text/html"}).status_code == 200, url


def test_unknown_addresses_are_404_with_the_not_found_page(site: Path) -> None:
    (site / "404.html").write_text('<html><meta name="robots" content="noindex">not found page</html>')
    client = TestClient(api)
    for path in ("/zz-not-a-page", "/fr/nope", "/check/nope", "/assets/nope.js"):
        response = client.get(path, headers={"Accept": "text/html"})  # used to be the app's shell, with a 200
        assert (response.status_code, "not found page" in response.text) == (404, True), path
        assert response.headers["content-type"].startswith("text/html")
    assert client.head("/zz-not-a-page").status_code == 404
    api_miss = client.get("/api/v1/nope", headers={"Accept": "text/html"})  # the API's own 404s stay JSON
    assert (api_miss.status_code, api_miss.json()) == (404, {"detail": "Not Found"})


@pytest.mark.usefixtures("site")
def test_unknown_addresses_are_404_without_a_build() -> None:
    response = TestClient(api).get("/zz-not-a-page", headers={"Accept": "text/html"})
    assert (response.status_code, response.json()) == (404, {"detail": "Not Found"})
