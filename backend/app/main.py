from collections.abc import Callable
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.api.main import api_router
from app.core.config import settings

FRONTEND_DIR = Path(__file__).parent / "frontend"


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.FASTAPI_ENV != "development":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_HOST],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Event streams, images and fonts are left alone by the middleware's default exclusions
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)

app.include_router(api_router, prefix=settings.API_V1_STR)

# The public pages, rendered to HTML at build time (frontend/src/prerender.tsx) so search engines and visitors get
# the page before the app's scripts run. "/" is the public page for visitors too; the app shows the signed-in its
# account page there, and index.html hides the rendered page from them meanwhile.
PRERENDERED = {
    "/": "check.html", "/check": "check.html", "/privacy": "privacy.html", "/terms": "terms.html",
    "/ontario-job-posting-requirements": "ontario-job-posting-requirements.html",
}  # fmt: skip


def _prerendered(name: str) -> Callable[[], FileResponse]:
    def page() -> FileResponse:
        for path in (FRONTEND_DIR / name, FRONTEND_DIR / "index.html"):  # a build without the pages: the app
            if path.is_file():
                return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)

    return page


for page_path, page_file in PRERENDERED.items():
    app.add_api_route(
        page_path, _prerendered(page_file), methods=["GET", "HEAD"], include_in_schema=False, tags=["pages"]
    )

app.frontend("/", directory=FRONTEND_DIR)
