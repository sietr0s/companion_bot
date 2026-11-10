"""Manager access-level composition; legacy URLs remain stable."""

from fastapi import APIRouter, Depends

from src.core.routers import create_manager_router
from src.core.runtime import require_external_services

from .accounts import router as accounts_router
from .chat_states import router as chat_states_router
from .configuration import router as configuration_router
from .settings import router as settings_router

module_router = APIRouter(prefix="/telegram")
router = create_manager_router(prefix="/public", tags=["Telegram Clients"])
module_router.include_router(configuration_router)
module_router.include_router(accounts_router, dependencies=[Depends(require_external_services)])
module_router.include_router(settings_router, dependencies=[Depends(require_external_services)])
module_router.include_router(chat_states_router, dependencies=[Depends(require_external_services)])

router.include_router(module_router)
