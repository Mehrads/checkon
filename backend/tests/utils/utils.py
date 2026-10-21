import random
import string
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings

LOGIN_CODE = "123456"


def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))


def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


def log_in(client: TestClient, *, email: str, password: str) -> dict[str, str]:
    """Log in with the password, then the sign-in code (fixed here, and not emailed)."""
    with (
        patch("app.core.security.new_login_code", return_value=LOGIN_CODE),
        patch("app.api.routes.login.send_email", return_value=True),
        patch("app.core.config.settings.LOGIN_CODES_PER_HOUR", 1000),
    ):
        r = client.post(
            f"{settings.API_V1_STR}/login/password",
            data={"username": email, "password": password},
        )
    challenge = r.json()["challenge"]
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        json={"challenge": challenge, "code": LOGIN_CODE},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def get_superuser_token_headers(client: TestClient) -> dict[str, str]:
    return log_in(
        client,
        email=settings.FIRST_SUPERUSER,
        password=settings.FIRST_SUPERUSER_PASSWORD,
    )
