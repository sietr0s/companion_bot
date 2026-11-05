"""Manager access-level composition; legacy URLs remain stable."""

from src.core.routers import create_manager_router

from .accounts import router as accounts_router
from .chat_states import router as chat_states_router
from .settings import router as settings_router

router = create_manager_router(prefix="/api/v1/public/telegram", tags=["Telegram Clients"])
router.include_router(accounts_router)
router.include_router(settings_router)
router.include_router(chat_states_router)
