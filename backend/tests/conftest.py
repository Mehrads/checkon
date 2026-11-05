import os

# Import the app without a built frontend (FastAPI skips that check in development).
os.environ.setdefault("FASTAPI_ENV", "development")


import pytest  # noqa: E402

from app.core.config import settings  # noqa: E402


@pytest.fixture(autouse=True)
def default_account_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Accounts as a fresh install has them, whatever the local .env holds: sign-up closed, no check limit."""
    monkeypatch.setattr(settings, "SIGNUP_OPEN", False)
    monkeypatch.setattr(settings, "ACCOUNT_CHECKS_PER_30_DAYS", 0)
