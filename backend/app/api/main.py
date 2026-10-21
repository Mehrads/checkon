from fastapi import APIRouter

from app.api.routes import billing, checks, items, login, private, stats, users, utils
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(checks.router)
api_router.include_router(billing.router)
api_router.include_router(stats.router)
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
