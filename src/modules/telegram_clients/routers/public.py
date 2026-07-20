"""Public API composition for the Telegram clients module."""

from fastapi import APIRouter

from src.modules.telegram_clients.routers.public_accounts import (
    router as accounts_router,
)
from src.modules.telegram_clients.routers.public_auth import router as auth_router
from src.modules.telegram_clients.routers.public_settings import (
    router as settings_router,
)
from src.modules.telegram_clients.routers.public_whitelist import router as whitelist_router

router = APIRouter(prefix="/api/v1/public/telegram", tags=["Telegram Clients"])
router.include_router(auth_router)
router.include_router(accounts_router)
router.include_router(settings_router)
router.include_router(whitelist_router)
