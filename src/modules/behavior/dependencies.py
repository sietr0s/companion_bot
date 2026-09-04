"""DI for behavior bus handlers."""

from src.bus.interface import MessageProducer
from src.core.config import settings
from src.modules.behavior.classifiers import ChatIntakeClassifier
from src.modules.behavior.repository import BehaviorRepository
from src.modules.behavior.service import BehaviorService
from src.modules.llm.dependencies import get_chat_provider


def build_behavior_service(producer: MessageProducer) -> BehaviorService:
    classifier = ChatIntakeClassifier(get_chat_provider(), settings.BEHAVIOR_INTAKE_TIMEOUT_S)
    return BehaviorService(producer, BehaviorRepository(), classifier)
