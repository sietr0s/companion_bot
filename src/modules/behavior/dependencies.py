"""DI for behavior bus handlers."""

from src.bus.interface import MessageProducer
from src.composition.ai import get_chat_provider
from src.domain.ai import ChatProvider
from src.modules.behavior.classifiers import ChatIntakeClassifier
from src.modules.behavior.config import get_settings
from src.modules.behavior.repository import BehaviorRepository
from src.modules.behavior.service import BehaviorService


def build_behavior_service(
    producer: MessageProducer, *, chat: ChatProvider | None = None
) -> BehaviorService:
    classifier = ChatIntakeClassifier(
        chat if chat is not None else get_chat_provider(), get_settings().BEHAVIOR_INTAKE_TIMEOUT_S
    )
    return BehaviorService(producer, BehaviorRepository(), classifier)
