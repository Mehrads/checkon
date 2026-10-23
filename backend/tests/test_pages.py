"""The public pages rendered at build time are served at their paths, "/" included; without them, the app's shell."""

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


def test_without_a_build_the_pages_are_404(site: Path) -> None:
    (site / "index.html").unlink()
    assert TestClient(api).get("/check").status_code == 404
