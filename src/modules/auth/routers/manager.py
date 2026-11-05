"""Manager-only administration of authentication accounts."""

from src.base.routers import create_crud_router
from src.core.routers import create_manager_router
from src.modules.auth.dependencies import get_auth_service
from src.modules.auth.schemas.api import AuthAccountCreate, AuthAccountRead, AuthAccountUpdate

router = create_manager_router(prefix="/api/v1/public/auth", tags=["Auth"])
router.include_router(
    create_crud_router(
        get_service=get_auth_service,
        create_schema=AuthAccountCreate,
        update_schema=AuthAccountUpdate,
        response_schema=AuthAccountRead,
        prefix="/accounts",
        tags=["Auth Accounts"],
        entity_name="Auth",
    )
)
