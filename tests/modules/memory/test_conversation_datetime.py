from sqlalchemy import DateTime

from src.modules.memory.models import Conversation


def test_last_activity_at_is_timezone_aware():
    column = Conversation.__table__.c.last_activity_at
    assert isinstance(column.type, DateTime)
    assert column.type.timezone is True
