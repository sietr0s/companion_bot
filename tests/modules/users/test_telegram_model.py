"""Модель User — собеседник Telegram."""

from src.modules.users.models import User


def test_user_tablename():
    assert User.__tablename__ == "user"


def test_user_has_telegram_id_and_notes():
    assert hasattr(User, "telegram_id")
    assert hasattr(User, "notes")
    assert not hasattr(User, "auth_id")
