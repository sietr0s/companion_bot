from src.base.configuration.routers import create_configuration_router
from src.modules.batching.config.dependencies import get_configuration_service

router = create_configuration_router(
    prefix="/api/v1/public/batching/configuration",
    get_service=get_configuration_service,
)
