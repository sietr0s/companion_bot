"""
Тесты конфигурации приложения.
"""

import os

from src.core.config import Settings, settings


class TestConfig:
    """Тесты загрузки и дефолтов настроек."""

    def test_settings_instance_exists(self):
        """Глобальный экземпляр настроек создан."""
        assert settings is not None

    def test_default_values(self):
        """Дефолтные значения корректны."""
        s = Settings(
            JWT_SECRET_KEY="test",
            DATABASE_URL="sqlite+aiosqlite:///test.db",
        )
        assert s.JWT_ALGORITHM == "HS256"
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 60 * 24
        assert s.MESSAGE_BUS == "in_memory"
        assert s.DATABASE_POOL_SIZE == 5
        assert s.DEBUG is False

    def test_env_override(self):
        """Переменные окружения переопределяют дефолты."""
        import os

        os.environ["DEBUG"] = "true"
        os.environ["MESSAGE_BUS"] = "kafka"
        try:
            s = Settings(
                JWT_SECRET_KEY="test",
                DATABASE_URL="sqlite+aiosqlite:///test.db",
            )
            assert s.DEBUG is True
            assert s.MESSAGE_BUS == "kafka"
        finally:
            del os.environ["DEBUG"]
            del os.environ["MESSAGE_BUS"]


def test_configure_langsmith_sets_env(monkeypatch):
    from types import SimpleNamespace

    from src.core import langsmith as ls

    monkeypatch.setattr(
        ls,
        "settings",
        SimpleNamespace(
            LANGSMITH_TRACING=True,
            LANGSMITH_API_KEY="ls-test",
            LANGSMITH_PROJECT="companion_bot",
            LANGSMITH_ENDPOINT="",
        ),
    )
    assert ls.configure_langsmith() is True
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGSMITH_PROJECT"] == "companion_bot"


def test_apply_model_cache_sets_env(tmp_path, monkeypatch):
    from src.core import model_cache as mc

    monkeypatch.setattr(mc.settings, "MODEL_CACHE_DIR", str(tmp_path / "models"))
    root = mc.apply_model_cache()
    assert (root / "huggingface" / "hub").is_dir()
    assert "huggingface" in os.environ["HF_HOME"]
    assert "sentence-transformers" in os.environ["SENTENCE_TRANSFORMERS_HOME"]
