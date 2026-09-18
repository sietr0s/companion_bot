"""Public API composition for Instagram clients."""

from fastapi import APIRouter, Depends

from src.base.routers import create_crud_router
from src.core.dependencies import get_current_admin
from src.modules.instagram_clients.dependencies import (
    get_instagram_account_service,
    get_instagram_chat_state_service,
    get_instagram_settings_service,
)
from src.modules.instagram_clients.routers.public_settings import router as settings_router
from src.modules.instagram_clients.routers.public_whitelist import router as whitelist_router
from src.modules.instagram_clients.schemas.public import (
    InstagramAccountCreate,
    InstagramAccountRead,
    InstagramAccountUpdate,
    InstagramChatStateCreate,
    InstagramChatStateRead,
    InstagramChatStateUpdate,
    InstagramSettingsCreate,
    InstagramSettingsRead,
    InstagramSettingsUpdate,
)

router = APIRouter(
    prefix="/api/v1/public/instagram",
    tags=["Instagram Clients"],
    dependencies=[Depends(get_current_admin)],
)
router.include_router(settings_router)
router.include_router(whitelist_router)
router.include_router(
    create_crud_router(
        get_service=get_instagram_account_service,
        create_schema=InstagramAccountCreate,
        update_schema=InstagramAccountUpdate,
        response_schema=InstagramAccountRead,
        prefix="/accounts",
        tags=["Instagram Accounts"],
        entity_name="InstagramAccount",
    )
)
router.include_router(
    create_crud_router(
        get_service=get_instagram_settings_service,
        create_schema=InstagramSettingsCreate,
        update_schema=InstagramSettingsUpdate,
        response_schema=InstagramSettingsRead,
        prefix="/settings",
        tags=["Instagram Settings"],
        entity_name="InstagramSettings",
    )
)
router.include_router(
    create_crud_router(
        get_service=get_instagram_chat_state_service,
        create_schema=InstagramChatStateCreate,
        update_schema=InstagramChatStateUpdate,
        response_schema=InstagramChatStateRead,
        prefix="/chat-states",
        tags=["Instagram Chat States"],
        entity_name="InstagramChatState",
    )
)
