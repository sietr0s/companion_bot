"""Manager access-level composition; legacy URLs remain stable."""

from fastapi import APIRouter

from src.core.routers import create_manager_router

from .accounts import router as accounts_router
from .chat_states import router as chat_states_router
from .settings import router as settings_router

module_router = APIRouter(prefix="/telegram")
router = create_manager_router(prefix="/public", tags=["Telegram Clients"])
module_router.include_router(accounts_router)
module_router.include_router(settings_router)
module_router.include_router(chat_states_router)

router.include_router(module_router)
