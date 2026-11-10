from .service import BehaviorConfigService


def get_configuration_service() -> BehaviorConfigService:
    return BehaviorConfigService()
