from pydantic import BaseModel


class WhitelistChatCreate(BaseModel):
    chat_id: int
