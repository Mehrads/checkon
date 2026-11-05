import warnings
from decimal import Decimal
from typing import Literal, Self

from pydantic import (
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    FASTAPI_ENV: Literal["development"] | None = None

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    # Claude API key for the Inspector and Refiner; without it the check endpoints return 503.
    ANTHROPIC_API_KEY: str | None = None

    # Langfuse traces of the model calls, metadata only (app/core/tracing.py). Off until both keys are set;
    # Terraform's placeholder secret ("replace-me") counts as not set.
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: str | None = None
    LANGFUSE_BASE_URL: str = "https://us.cloud.langfuse.com"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tracing_enabled(self) -> bool:
        return all(key and key != "replace-me" for key in (self.LANGFUSE_PUBLIC_KEY, self.LANGFUSE_SECRET_KEY))

    # Where contact-form messages are emailed (needs the SMTP settings below); they are always saved.
    CONTACT_EMAIL: EmailStr | None = None

    # The free check's limits, for visitors who aren't signed in
    FREE_CHECKS_PER_WEEK: int = 1
    FREE_CHECK_DAILY_SPEND_CAP_USD: Decimal = Decimal("5")
    FREE_CHECK_REQUESTS_PER_MINUTE: int = 30
    # Posting links the server fetches per IP per hour, for free and paid checks alike. A link that can't be
    # read uses no check, so this bounds the fetches a visitor can make.
    LINK_FETCHES_PER_HOUR: int = 20
    # Proxies in front of the app that append to X-Forwarded-For (Cloud Run: 1). The client IP is
    # read that many entries from the right, so a client can't spoof it by sending its own header.
    TRUSTED_PROXY_HOPS: int = 0
    # Browser extensions allowed to call the free check, by ID, comma-separated (extension/README.md).
    EXTENSION_IDS: str = ""
    # Addresses that skip the weekly quota, comma-separated, so you can test the live check yourself.
    # The rate limit, the origin check and the daily spend cap still apply to them.
    FREE_CHECK_ALLOWLIST_IPS: str = ""
    # The free sample audit on the public site: the first postings of a careers page, findings only, on the same
    # daily spend cap and allowlist as the free check, with its own weekly quota.
    SAMPLE_AUDITS_PER_WEEK: int = 1
    SAMPLE_AUDIT_POSTINGS: int = 3

    # Signed-in accounts (app/api/accounts.py). Whoever runs the server pays the model fees, so sign-up is off
    # until SIGNUP_OPEN is set (an admin can still add users), and each account can be held to a number of checks
    # in any 30 days (0: no limit). Sign-ups per IP per hour, when it's open.
    SIGNUP_OPEN: bool = False
    ACCOUNT_CHECKS_PER_30_DAYS: int = 0
    SIGNUPS_PER_HOUR: int = 5

    DATABASE_URL: PostgresDsn

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _use_psycopg_driver(cls, value: str | PostgresDsn) -> str:
        database_url = str(value)
        for scheme in ("postgres://", "postgresql://"):
            if database_url.startswith(scheme):
                return database_url.replace(scheme, "postgresql+psycopg://", 1)
        return database_url

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    # Logging in takes the password, then a 6-digit code emailed to the account (needs SMTP).
    LOGIN_CODE_EXPIRE_MINUTES: int = 10
    LOGIN_CODE_MAX_ATTEMPTS: int = 5
    LOGIN_CODES_PER_HOUR: int = 5

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.FASTAPI_ENV == "development":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        for host in self.DATABASE_URL.hosts():
            self._check_default_secret("DATABASE_URL password", host["password"])
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


settings = Settings()  # type: ignore # ty: ignore[unused-ignore-comment]
