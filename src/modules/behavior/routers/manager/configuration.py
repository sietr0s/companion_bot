from src.base.configuration.routers import create_configuration_router
from src.modules.behavior.config.dependencies import get_configuration_service

router = create_configuration_router(prefix="/configuration", get_service=get_configuration_service)
