import pytest

from src.modules.behavior.classifiers import ChatIntakeClassifier


@pytest.mark.asyncio
async def test_classifier_bad_json_fail_open():
    class Bad:
        async def complete(self, system, user):
            return "nope"

    c = ChatIntakeClassifier(Bad(), timeout_s=1)
    assert await c.classify("hi") == (1, 0)
