"""Модель User — собеседник Telegram."""

from src.modules.users.models import User


def test_user_tablename():
    assert User.__tablename__ == "user"


def test_user_has_platform_and_notes():
    assert hasattr(User, "platform")
    assert hasattr(User, "platform_user_id")
    assert hasattr(User, "notes")
    assert not hasattr(User, "telegram_id")
    assert not hasattr(User, "auth_id")
