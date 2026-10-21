import os

# Import the app without a built frontend (FastAPI skips that check in development).
os.environ.setdefault("FASTAPI_ENV", "development")


import pytest  # noqa: E402

from app.core.config import settings  # noqa: E402


@pytest.fixture(autouse=True)
def no_real_stripe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stripe stays off whatever the local .env holds, so no test reaches Stripe's API (tests that need it
    set fake values and a fake client)."""
    for name in ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_STARTER", "STRIPE_PRICE_AGENCY",
                 "STRIPE_PRICE_EXTRA_CHECK"):  # fmt: skip
        monkeypatch.setattr(settings, name, None)
