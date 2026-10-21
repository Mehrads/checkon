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

    # Where contact-form messages are emailed (needs the SMTP settings above); they are always saved.
    CONTACT_EMAIL: EmailStr | None = None

    # Free check limits (04-V1-Scope.md, section 4)
    FREE_CHECKS_PER_WEEK: int = 1
    FREE_CHECK_DAILY_SPEND_CAP_USD: Decimal = Decimal("5")
    FREE_CHECK_REQUESTS_PER_MINUTE: int = 30
    # Proxies in front of the app that append to X-Forwarded-For (Cloud Run: 1). The client IP is
    # read that many entries from the right, so a client can't spoof it by sending its own header.
    TRUSTED_PROXY_HOPS: int = 0
    # Browser extensions allowed to call the free check, by ID, comma-separated (extension/README.md).
    EXTENSION_IDS: str = ""

    # Paid plans through Stripe Billing (infra/README.md, "Stripe"). Until the key and the three prices are
    # set, Checkout is off and the pricing page offers the contact form instead.
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_STARTER: str | None = None
    STRIPE_PRICE_AGENCY: str | None = None
    STRIPE_PRICE_EXTRA_CHECK: str | None = None  # the usage-based price on the extra-check meter
    STRIPE_METER_EVENT: str = "checkon_extra_check"  # the meter's event name
    STRIPE_AUTOMATIC_TAX: bool = False  # Stripe Tax adds HST; turn on once registered
    PLAN_CHECKS_STARTER: int = 50
    PLAN_CHECKS_AGENCY: int = 300
    # Extra checks a customer can run in one billing period before checks stop until the next one
    PLAN_EXTRA_CHECKS_MAX: int = 200

    @computed_field  # type: ignore[prop-decorator]
    @property
    def billing_enabled(self) -> bool:
        return bool(
            self.STRIPE_SECRET_KEY
            and self.STRIPE_PRICE_STARTER
            and self.STRIPE_PRICE_AGENCY
            and self.STRIPE_PRICE_EXTRA_CHECK
        )

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
