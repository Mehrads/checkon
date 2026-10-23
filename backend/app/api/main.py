from fastapi import APIRouter

from app.api.routes import audits, billing, checks, items, login, pay, private, stats, users, utils, workspaces
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(checks.router)
api_router.include_router(billing.router)
api_router.include_router(workspaces.router)
api_router.include_router(pay.router)
api_router.include_router(audits.router)
api_router.include_router(stats.router)
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
