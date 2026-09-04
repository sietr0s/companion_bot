from src.modules.behavior.filters import voice_block_reason
from src.modules.behavior.scoring import detect_emotion, strip_emotion_suffix


def test_digits_and_url_block_voice():
    assert voice_block_reason("call 89001234567") == "digits"
    assert voice_block_reason("see https://t.me/x") == "url"
    assert voice_block_reason("ok hi") == "short"


def test_strip_emotion_suffix():
    body, emo = strip_emotion_suffix('hello\n{"emotion": 1}')
    assert body == "hello"
    assert emo == 1


def test_detect_emotion_exclamation():
    assert detect_emotion("wow!") == 1
    assert detect_emotion("ok", llm_emotion=1) == 1
    assert detect_emotion("ok") == 0
