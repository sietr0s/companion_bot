"""DI for behavior bus handlers."""

from src.bus.interface import MessageProducer
from src.composition.ai import get_chat_provider
from src.modules.behavior.classifiers import ChatIntakeClassifier
from src.modules.behavior.config import behavior_settings
from src.modules.behavior.repository import BehaviorRepository
from src.modules.behavior.service import BehaviorService


def build_behavior_service(producer: MessageProducer) -> BehaviorService:
    classifier = ChatIntakeClassifier(
        get_chat_provider(), behavior_settings.BEHAVIOR_INTAKE_TIMEOUT_S
    )
    return BehaviorService(producer, BehaviorRepository(), classifier)
