from src.base.service import BaseService
from src.modules.instagram_clients.models import InstagramChatState
from src.modules.instagram_clients.repository import InstagramChatStateRepository


class InstagramChatStateService(BaseService[InstagramChatStateRepository, InstagramChatState]):
    def __init__(self, repository: InstagramChatStateRepository) -> None:
        super().__init__(repository)
