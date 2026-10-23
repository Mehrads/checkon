from collections.abc import Callable
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, Response
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException
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
    # One page per rule (frontend/src/components/Site/rules), in English and French
    "/ontario-pay-transparency-job-posting": "ontario-pay-transparency-job-posting.html",
    "/ontario-canadian-experience-job-posting": "ontario-canadian-experience-job-posting.html",
    "/ontario-ai-disclosure-job-posting": "ontario-ai-disclosure-job-posting.html",
    "/ontario-existing-vacancy-job-posting": "ontario-existing-vacancy-job-posting.html",
    "/ontario-45-day-interview-response": "ontario-45-day-interview-response.html",
    "/ontario-job-posting-record-keeping": "ontario-job-posting-record-keeping.html",
    "/fr/ontario-transparence-salariale-offre-emploi": "fr-ontario-transparence-salariale-offre-emploi.html",
    "/fr/ontario-experience-canadienne-offre-emploi": "fr-ontario-experience-canadienne-offre-emploi.html",
    "/fr/ontario-divulgation-ia-offre-emploi": "fr-ontario-divulgation-ia-offre-emploi.html",
    "/fr/ontario-poste-vacant-existant-offre-emploi": "fr-ontario-poste-vacant-existant-offre-emploi.html",
    "/fr/ontario-reponse-45-jours-entrevue": "fr-ontario-reponse-45-jours-entrevue.html",
    "/fr/ontario-conservation-offres-emploi": "fr-ontario-conservation-offres-emploi.html",
}  # fmt: skip

# The app's own pages (frontend/src/routes): its shell, index.html, which keeps them out of search results.
APP_PAGES = (
    "/login", "/recover-password", "/reset-password", "/welcome", "/admin", "/archive", "/profile", "/settings",
    "/stats", "/audits", "/audits/{audit_id}", "/audits/{audit_id}/{posting_id}",
)  # fmt: skip


def _prerendered(name: str) -> Callable[[], FileResponse]:
    def page() -> FileResponse:
        for path in (FRONTEND_DIR / name, FRONTEND_DIR / "index.html"):  # a build without the pages: the app
            if path.is_file():
                return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)

    return page


for page_path, page_file in [*PRERENDERED.items(), *((path, "index.html") for path in APP_PAGES)]:
    app.add_api_route(
        page_path, _prerendered(page_file), methods=["GET", "HEAD"], include_in_schema=False, tags=["pages"]
    )

# Any other address the build's files don't have is a 404 (below), so search engines don't take it for a page. In
# development there may be no build (the tests, CI's backend job); production refuses to start without one.
if FRONTEND_DIR.is_dir() or settings.FASTAPI_ENV != "development":
    app.frontend("/", directory=FRONTEND_DIR, fallback=None)


@app.exception_handler(StarletteHTTPException)
async def not_found_page(request: Request, exc: StarletteHTTPException) -> Response:
    """Outside the API, "not found" is the build's 404.html: the app's not-found page, kept out of search results."""
    page = FRONTEND_DIR / "404.html"
    if exc.status_code == 404 and not request.url.path.startswith(settings.API_V1_STR) and page.is_file():
        return FileResponse(page, status_code=404, media_type="text/html")
    return await http_exception_handler(request, exc)
