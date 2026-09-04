# Behavior modality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Companion chooses ignore vs generate before LLM, then text vs voice after, via a new `behavior` module with persisted life state, weighted softmax, and TTS send with text fallback.

**Architecture:** Orchestrator publishes `behavior.command.decide_intake` after `MEMORY_CONTEXT_BUILT`. Ignore stops the turn (memory already stored). Respond goes to existing LLM generate. After `LLM_REPLY_GENERATED`, `decide_delivery` picks text (current `send_message`) or voice (`record_audio` + sleep + TTS; skip → text). `note_delivery` updates chat streak. Life rolls lazily on intake.

**Tech Stack:** existing in-memory/Kafka bus, SQLAlchemy + Alembic, ChatProvider for intake JSON, Telethon send_file/voice, pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-09-03-behavior-modality-design.md`

## Global Constraints

- New module `src/modules/behavior/` owns scoring, life, persistence. Orchestrator does not import behavior repository.
- v1 actions only: intake `{ignore, respond}`, delivery `{text, voice}`. Enum may list `delay`/`sticker` with weight 0; they must not win.
- Hard filters zero voice even if `asked_voice=1`.
- Intake classifier fail-open: `needs_reply=1`, `asked_voice=0`.
- Missing `telegram_account_id`: intake `respond`, delivery `text`.
- Tests never call a real ChatProvider / Whisper / TTS engine; inject fakes.
- `datetime.now(UTC)` in app code; night hours via `BEHAVIOR_TIMEZONE` (default `Europe/Moscow`), hours 22–05 inclusive.
- Weights live as constants on `Criterion` / `Policy` classes, not env vars.
- New parameters = new `Criterion` appended to a `Policy`. New choices = `legal_actions` + orchestrator branch. Engine (`decide`) stays unchanged.
- Voice send failure after TTS: do not auto-resend text.
- Incoming is still written to memory on ignore.

## File map

| File | Responsibility |
|------|----------------|
| `src/core/bus_topics.py` | behavior + send_voice topics |
| `src/core/config.py` | `BEHAVIOR_TIMEZONE`, `BEHAVIOR_SOFTMAX_TEMP`, `BEHAVIOR_INTAKE_TIMEOUT_S` |
| `src/modules/behavior/engine.py` | `DecisionContext`, `Policy`, `decide`, noise, softmax |
| `src/modules/behavior/criteria.py` | one class per scoring parameter |
| `src/modules/behavior/filters.py` | hard blockers (voice digits/url/markup/short) |
| `src/modules/behavior/policies.py` | `INTAKE_POLICY`, `DELIVERY_POLICY` |
| `src/modules/behavior/scoring.py` | emotion strip/detect, word_count helpers |
| `src/modules/behavior/life.py` | roll activity/mood |
| `src/modules/behavior/models.py` | two tables |
| `src/modules/behavior/repository.py` | get-or-create, note delivery |
| `src/modules/behavior/classifiers.py` | protocol + ChatProvider adapter |
| `src/modules/behavior/prompts/intake.md` | JSON-only intake prompt |
| `src/modules/behavior/schemas/events.py` | commands/events |
| `src/modules/behavior/service.py` | decide_intake / decide_delivery / note_delivery |
| `src/modules/behavior/handlers.py` | bus subscriptions |
| `src/modules/behavior/dependencies.py` | `build_behavior_service` |
| `alembic/versions/20260904_behavior_state.py` | migration |
| `src/modules/orchestrator/service.py` | route intake/delivery/TTS |
| `src/modules/orchestrator/schemas/state.py` | `batch_messages`, pending voice text |
| `src/modules/telegram_clients/adapters/client_manager.py` | `send_voice`, `send_chat_action` |
| `src/modules/telegram_clients/handlers.py` | `TG_MESSAGE_SEND_VOICE` |
| `src/modules/llm/prompts/reply.md` | optional emotion JSON line |
| `src/main.py` | register behavior handlers |
| `alembic/env.py` | import behavior models |

---

### Task 1: Topics, settings, event schemas

**Files:**
- Modify: `src/core/bus_topics.py`
- Modify: `src/core/config.py`
- Modify: `.env.example` if it lists STT/TTS (add the three BEHAVIOR keys)
- Create: `src/modules/behavior/__init__.py`, `exceptions.py`, `schemas/__init__.py`, `schemas/events.py`
- Test: `tests/modules/behavior/test_events.py`

**Interfaces:**
- Produces:

```python
# BusTopics
BEHAVIOR_DECIDE_INTAKE = "behavior.command.decide_intake"
BEHAVIOR_INTAKE_DECIDED = "behavior.event.intake_decided"
BEHAVIOR_DECIDE_DELIVERY = "behavior.command.decide_delivery"
BEHAVIOR_DELIVERY_DECIDED = "behavior.event.delivery_decided"
BEHAVIOR_NOTE_DELIVERY = "behavior.command.note_delivery"
TG_MESSAGE_SEND_VOICE = "telegram_clients.command.send_voice"

# Settings defaults
BEHAVIOR_TIMEZONE: str = "Europe/Moscow"
BEHAVIOR_SOFTMAX_TEMP: float = 1.0
BEHAVIOR_INTAKE_TIMEOUT_S: float = 8.0
```

```python
from uuid import UUID
from pydantic import BaseModel, Field
from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Message

class DecideIntakeCommand(BaseModel):
    conversation_id: UUID
    telegram_account_id: UUID | None = None
    telegram_chat_id: int
    context: str = ""
    batch_messages: list[Message] = Field(default_factory=list)

class IntakeDecidedEvent(BaseEvent):
    event_name: str = BusTopics.BEHAVIOR_INTAKE_DECIDED
    conversation_id: UUID
    telegram_account_id: UUID | None = None
    telegram_chat_id: int
    action: str  # ignore | respond
    scores: dict[str, float] = Field(default_factory=dict)
    activity: str | None = None
    mood: str | None = None
    needs_reply: int = 1
    asked_voice: int = 0

class DecideDeliveryCommand(BaseModel):
    conversation_id: UUID
    telegram_account_id: UUID | None = None
    telegram_chat_id: int
    messages: list[Message] = Field(default_factory=list)
    batch_messages: list[Message] = Field(default_factory=list)
    asked_voice: int = 0
    emotion: int | None = None

class DeliveryDecidedEvent(BaseEvent):
    event_name: str = BusTopics.BEHAVIOR_DELIVERY_DECIDED
    conversation_id: UUID
    telegram_account_id: UUID | None = None
    telegram_chat_id: int
    action: str  # text | voice
    text: str
    scores: dict[str, float] = Field(default_factory=dict)
    blocked_voice: bool = False
    block_reasons: list[str] = Field(default_factory=list)

class NoteDeliveryCommand(BaseModel):
    telegram_account_id: UUID
    telegram_chat_id: int
    channel: str  # text | voice
```

- [ ] **Step 1: Write the failing test**

```python
from src.core.bus_topics import BusTopics
from src.core.config import Settings
from src.modules.behavior.schemas.events import DecideIntakeCommand, IntakeDecidedEvent

def test_behavior_topics_exist():
    assert BusTopics.BEHAVIOR_DECIDE_INTAKE == "behavior.command.decide_intake"
    assert BusTopics.TG_MESSAGE_SEND_VOICE == "telegram_clients.command.send_voice"

def test_behavior_settings_defaults():
    s = Settings(JWT_SECRET_KEY="t", ADMIN_EMAIL="a@b.c", ADMIN_PASSWORD="p")
    assert s.BEHAVIOR_TIMEZONE == "Europe/Moscow"
    assert s.BEHAVIOR_SOFTMAX_TEMP == 1.0
    assert s.BEHAVIOR_INTAKE_TIMEOUT_S == 8.0

def test_intake_event_roundtrip():
    from uuid import uuid4
    ev = IntakeDecidedEvent(
        conversation_id=uuid4(),
        telegram_chat_id=1,
        action="respond",
    )
    data = ev.to_bus_dict()
    assert data["event_name"] == BusTopics.BEHAVIOR_INTAKE_DECIDED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/modules/behavior/test_events.py -v`  
Expected: FAIL (module / attributes missing)

- [ ] **Step 3: Add topics, settings, schemas** as in Interfaces.

- [ ] **Step 4: Run tests**

Run: `pytest tests/modules/behavior/test_events.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/bus_topics.py src/core/config.py src/modules/behavior tests/modules/behavior/test_events.py .env.example
git commit -m "feat(behavior): bus topics, settings, and event schemas"
```

---

### Task 2: Policy engine + criteria + filters

**Files:**
- Create: `src/modules/behavior/engine.py`, `criteria.py`, `filters.py`, `policies.py`, `scoring.py`
- Test: `tests/modules/behavior/test_engine.py`, `tests/modules/behavior/test_criteria.py`, `tests/modules/behavior/test_scoring.py`

**Interfaces:**
- Consumes: `settings.BEHAVIOR_TIMEZONE`, `settings.BEHAVIOR_SOFTMAX_TEMP`
- Produces:

```python
# engine.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Protocol
import random

@dataclass(frozen=True)
class LifeSnapshot:
    activity: str
    mood: str

@dataclass(frozen=True)
class ChatSnapshot:
    consecutive_voice_out: int
    last_delivery: str | None

@dataclass
class DecisionContext:
    incoming_text: str = ""
    incoming_types: tuple[str, ...] = ()
    outgoing_text: str = ""
    life: LifeSnapshot = LifeSnapshot("working", "neutral")
    chat: ChatSnapshot = ChatSnapshot(0, None)
    needs_reply: int = 1
    asked_voice: int = 0
    emotion: int = 0
    now: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)

class Criterion(Protocol):
    name: str
    def deltas(self, ctx: DecisionContext) -> Mapping[str, float]: ...

class ActionFilter(Protocol):
    name: str
    def blocked(self, ctx: DecisionContext) -> Mapping[str, str]: ...

@dataclass(frozen=True)
class Policy:
    name: str
    legal_actions: tuple[str, ...]
    base_weights: dict[str, float]
    criteria: tuple[Criterion, ...]
    filters: tuple[ActionFilter, ...]
    fallback: str

@dataclass(frozen=True)
class Decision:
    action: str
    scores: dict[str, float]
    blocked: dict[str, str]

def apply_noise(weights: dict[str, float], rng: random.Random) -> dict[str, float]: ...
def softmax_sample(weights: dict[str, float], rng: random.Random, temperature: float = 1.0, fallback: str = "text") -> str: ...

def decide(policy: Policy, ctx: DecisionContext, rng: random.Random, temperature: float | None = None) -> Decision:
    """base → sum deltas for legal actions only → zero blocked → noise → softmax.
    Unknown action keys from criteria are dropped. All-zero → policy.fallback."""
```

```python
# scoring.py — helpers only
def word_count(text: str) -> int: ...
def strip_emotion_suffix(text: str) -> tuple[str, int | None]: ...
def detect_emotion(text: str, llm_emotion: int | None = None) -> int: ...
def local_hour(now: datetime, tz_name: str) -> int: ...
```

```python
# filters.py
class VoiceHardFilter:
    name = "voice_hard"
    def blocked(self, ctx: DecisionContext) -> dict[str, str]:
        """If digits/url/markup/short on outgoing_text → {"voice": reason}."""
```

Criteria (each a class with `name` and `deltas`). Numbers from the spec tables:

| Class | Emits |
|---|---|
| `NeedsReplyCriterion` | needs_reply 0 → ignore +40; 1 → ignore −25 |
| `GreetingIntakeCriterion` | short greeting → ignore +5 |
| `LifeIgnoreCriterion` | working +5 / resting +15 / running +10 / public +15 on ignore |
| `MoodIgnoreCriterion` | good ignore −10; bad ignore +25 |
| `OutgoingLengthCriterion` | outgoing >15 words → voice +25, text −10 |
| `MirrorVoiceCriterion` | incoming type voice/audio → voice +30, text −10 |
| `VoiceStreakCriterion` | streak 1–2 voice +10; ≥4 voice −40 text +25 |
| `StyleSwitchCriterion` | last text and outgoing >15 → voice +15 |
| `NightVoiceCriterion` | local hour 22–05 → voice +20, text −10 |
| `IncomingLengthCriterion` | incoming >20 words → voice +15, text −5 |
| `GreetingDeliveryCriterion` | short greeting → text +15, voice −20 |
| `LifeDeliveryCriterion` | working/resting/running/public text/voice deltas from spec |
| `MoodDeliveryCriterion` | good text +5; bad text −10 voice −10 |
| `AskedVoiceCriterion` | asked_voice=1 → voice +50 |
| `WantSpeakCriterion` | activity resting/running → voice +10 |
| `EmotionVoiceCriterion` | emotion=1 → voice +20, text −5 |

`policies.py` builds `INTAKE_POLICY` and `DELIVERY_POLICY` as in the spec. Service (Task 4) only calls `decide(INTAKE_POLICY, ctx, rng)` / `decide(DELIVERY_POLICY, ...)`.

Night: `local_hour` uses `BEHAVIOR_TIMEZONE`. Greeting: `word_count <= 3` and first token lowercased in `{привет, здарова, хай, йо}`.

- [ ] **Step 1: Write failing tests**

Engine plugin test (this is the extensibility contract):

```python
import random
from datetime import UTC, datetime
from src.modules.behavior.engine import (
    DecisionContext, Policy, decide, softmax_sample,
)

class BoostSticker:
    name = "boost_sticker"
    def deltas(self, ctx):
        return {"sticker": 100.0, "text": -5.0}

def test_new_action_is_opt_in_via_legal_actions():
    rng = random.Random(0)
    ctx = DecisionContext(now=datetime.now(UTC))
    policy = Policy(
        name="t",
        legal_actions=("text", "sticker"),
        base_weights={"text": 10, "sticker": 0},
        criteria=(BoostSticker(),),
        filters=(),
        fallback="text",
    )
    d = decide(policy, ctx, rng)
    assert d.action == "sticker"
    assert "sticker" in d.scores

def test_unknown_delta_keys_are_dropped():
    rng = random.Random(0)
    policy = Policy(
        name="t",
        legal_actions=("text",),
        base_weights={"text": 10},
        criteria=(BoostSticker(),),
        filters=(),
        fallback="text",
    )
    d = decide(policy, ctx := DecisionContext(), rng)
    assert "sticker" not in d.scores
    assert d.action == "text"

def test_softmax_all_zero_fallback():
    rng = random.Random(0)
    assert softmax_sample({"text": 0, "voice": 0}, rng, fallback="text") == "text"
```

Filters + policies (use `decide` with `apply_noise` disabled by monkeypatching `apply_noise` to identity, or inspect `Decision.scores` after a criterion-only policy):

```python
from src.modules.behavior.filters import VoiceHardFilter
from src.modules.behavior.engine import DecisionContext, LifeSnapshot, ChatSnapshot
from src.modules.behavior.policies import DELIVERY_POLICY, INTAKE_POLICY
from src.modules.behavior.engine import decide
from src.modules.behavior.scoring import strip_emotion_suffix, detect_emotion

def test_voice_hard_filter_blocks_digits():
    ctx = DecisionContext(outgoing_text="call 89001234567 extra words here")
    blocked = VoiceHardFilter().blocked(ctx)
    assert blocked.get("voice")

def test_delivery_policy_cannot_pick_voice_when_blocked():
    rng = random.Random(0)
    ctx = DecisionContext(
        outgoing_text="https://t.me/x and more words in this reply",
        asked_voice=1,
        emotion=1,
        life=LifeSnapshot("resting", "good"),
        now=datetime(2026, 1, 1, 23, tzinfo=UTC),
    )
    for _ in range(20):
        assert decide(DELIVERY_POLICY, ctx, rng).action != "voice"

def test_intake_needs_reply_zero_raises_ignore_score():
    rng = random.Random(0)
    life = LifeSnapshot("working", "neutral")
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)
    a = decide(INTAKE_POLICY, DecisionContext(incoming_text="long message here", life=life, needs_reply=0, now=now), rng)
    b = decide(INTAKE_POLICY, DecisionContext(incoming_text="long message here", life=life, needs_reply=1, now=now), rng)
    assert a.scores["ignore"] > b.scores["ignore"]

def test_strip_emotion_suffix():
    body, emo = strip_emotion_suffix("hello\n{\"emotion\": 1}")
    assert body == "hello" and emo == 1
```

Also test `OutgoingLengthCriterion` / `VoiceStreakCriterion` / `NightVoiceCriterion` deltas in isolation (call `.deltas(ctx)` and assert numbers from the spec).

- [ ] **Step 2: Run tests — expect FAIL**

Run: `pytest tests/modules/behavior/test_engine.py tests/modules/behavior/test_criteria.py tests/modules/behavior/test_scoring.py -v`

- [ ] **Step 3: Implement engine, criteria, filters, policies, scoring helpers.** Filters: `re.search(r"\d{5,}")`; `http://|https://|t.me/`; backticks or line starting with `#` or `|`; `word_count < 4`.

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/modules/behavior/engine.py src/modules/behavior/criteria.py src/modules/behavior/filters.py src/modules/behavior/policies.py src/modules/behavior/scoring.py tests/modules/behavior/test_engine.py tests/modules/behavior/test_criteria.py tests/modules/behavior/test_scoring.py
git commit -m "feat(behavior): pluggable policy engine for criteria and actions"
```

---

### Task 3: Life roll, models, repository, migration

**Files:**
- Create: `src/modules/behavior/life.py`, `models.py`, `repository.py`
- Modify: `alembic/env.py` (import models)
- Create: `alembic/versions/20260904_behavior_state.py`
- Test: `tests/modules/behavior/test_life.py`, `tests/modules/behavior/test_repository.py`

**Interfaces:**
- Consumes: `LifeSnapshot` from `engine.py`
- Produces:

```python
# life.py
from datetime import datetime, timedelta, UTC
from src.modules.behavior.engine import LifeSnapshot
import random

ACTIVITIES = ("working", "resting", "running", "public")
MOODS = ("good", "neutral", "bad")

def should_roll(activity_until: datetime | None, now: datetime) -> bool:
    return activity_until is None or activity_until <= now

def roll_life(now: datetime, rng: random.Random) -> tuple[LifeSnapshot, datetime]:
    life = LifeSnapshot(rng.choice(list(ACTIVITIES)), rng.choice(list(MOODS)))
    hours = rng.uniform(2.0, 4.0)
    until = now + timedelta(hours=hours)
    return life, until
```

```python
# models.py — BehaviorAccountState: PK account_id (no extra UUID pk)
# BehaviorChatState: BaseModel UUID pk, unique (account_id, chat_id)
```

`BehaviorAccountState` inherits `src.base.model.Base` (not `BaseModel`) so `account_id` is the only PK. Include `updated_at`. FK `telegram_account.id` ON DELETE CASCADE.

`BehaviorChatState` inherits `BaseModel`. Columns: `account_id`, `chat_id` BigInteger, `consecutive_voice_out` default 0, `last_delivery` String nullable.

```python
class BehaviorRepository:
    async def get_or_create_account(self, session, account_id: UUID, now: datetime, rng) -> BehaviorAccountState:
        """Insert defaults working/neutral/until=now+3h if missing. If should_roll, apply roll_life and persist."""

    async def get_or_create_chat(self, session, account_id: UUID, chat_id: int) -> BehaviorChatState:
        ...

    async def note_delivery(self, session, account_id: UUID, chat_id: int, channel: str) -> None:
        """voice: consecutive += 1, last_delivery=voice. text: consecutive=0, last_delivery=text."""
```

- [ ] **Step 1: Failing tests**

```python
from datetime import UTC, datetime, timedelta
from uuid import uuid4
import random
from src.modules.behavior.life import roll_life, should_roll

def test_should_roll_when_expired():
    now = datetime.now(UTC)
    assert should_roll(now - timedelta(seconds=1), now) is True
    assert should_roll(now + timedelta(hours=1), now) is False
    assert should_roll(None, now) is True

def test_roll_life_until_between_2_and_4_hours():
    now = datetime.now(UTC)
    life, until = roll_life(now, random.Random(0))
    assert life.activity in {"working", "resting", "running", "public"}
    delta = (until - now).total_seconds()
    assert 2 * 3600 <= delta <= 4 * 3600
```

Repository test uses `db_session` fixture (same as memory tests). Create a `TelegramAccount` row first (required FK) or use the existing account factory if tests have one. If no factory, insert `TelegramAccount` with required `phone` / `session_file` fields.

```python
@pytest.mark.asyncio
async def test_note_delivery_resets_streak_on_text(db_session):
    ...
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement models, life, repository, alembic revision** (hand-written like `9f37893a21c4_add_telegram_chat_state_table.py`: `op.create_table` for both). Import models in `alembic/env.py`.

- [ ] **Step 4: Run**

Run: `pytest tests/modules/behavior/test_life.py tests/modules/behavior/test_repository.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/modules/behavior/life.py src/modules/behavior/models.py src/modules/behavior/repository.py alembic/env.py alembic/versions/20260904_behavior_state.py tests/modules/behavior/test_life.py tests/modules/behavior/test_repository.py
git commit -m "feat(behavior): persist account life and chat voice streak"
```

---

### Task 4: Intake classifier, service, handlers

**Files:**
- Create: `src/modules/behavior/prompts/intake.md`, `classifiers.py`, `service.py`, `handlers.py`, `dependencies.py`
- Modify: `src/main.py` (`register_behavior_handlers`)
- Test: `tests/modules/behavior/test_classifier.py`, `tests/modules/behavior/test_service.py`

**Interfaces:**
- Consumes: scoring, life, repository, `ChatProvider`, `Decide*Command`
- Produces:

```python
class IntakeClassifier(Protocol):
    async def classify(self, user_text: str) -> tuple[int, int]:
        """Return (needs_reply, asked_voice), each 0 or 1."""

class FakeIntakeClassifier:
    def __init__(self, needs_reply: int = 1, asked_voice: int = 0) -> None: ...
    async def classify(self, user_text: str) -> tuple[int, int]: ...

class ChatIntakeClassifier:
    def __init__(self, chat: ChatProvider, timeout_s: float) -> None: ...
    async def classify(self, user_text: str) -> tuple[int, int]:
        """complete(intake prompt, user_text); parse JSON; on timeout/error/bad JSON → (1, 0)."""

class BehaviorService:
    def __init__(self, producer: MessageProducer, repo: BehaviorRepository, classifier: IntakeClassifier, rng: random.Random | None = None) -> None: ...
    async def decide_intake(self, session, command: DecideIntakeCommand) -> IntakeDecidedEvent
    async def decide_delivery(self, session, command: DecideDeliveryCommand) -> DeliveryDecidedEvent
    async def note_delivery(self, session, command: NoteDeliveryCommand) -> None
```

`intake.md`:

```markdown
You classify whether a chat message needs a reply.
Reply with JSON only, no markdown:
{"needs_reply": 0, "asked_voice": 0}
needs_reply=1 if a human would answer. asked_voice=1 only if they asked for a voice message.
```

`decide_intake`: if no `telegram_account_id` → publish `action=respond`, scores `{respond: 50, ignore: 0}`, skip DB. Else load/roll account, classify with timeout `asyncio.wait_for(..., BEHAVIOR_INTAKE_TIMEOUT_S)`, build `DecisionContext`, `decision = decide(INTAKE_POLICY, ctx, rng)`. Persist asked_voice only in the event (not DB). Publish `IntakeDecidedEvent`.

`decide_delivery`: concatenate outgoing texts with `. `; `strip_emotion_suffix` on that string; `detect_emotion`; if no account_id → `action=text`. Else load chat+account (same get_or_create_account). `decide(DELIVERY_POLICY, ctx, rng)`. Publish event with `text` = stripped body.

`dependencies.build_behavior_service(producer)`: repo + `ChatIntakeClassifier(get_chat_provider(), settings.BEHAVIOR_INTAKE_TIMEOUT_S)`.

Handlers mirror memory: `create_async_session`, `model_validate`.

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.asyncio
async def test_classifier_bad_json_fail_open():
    class Bad:
        async def complete(self, system, user):
            return "nope"
    c = ChatIntakeClassifier(Bad(), timeout_s=1)
    assert await c.classify("hi") == (1, 0)

@pytest.mark.asyncio
async def test_decide_intake_ignore_when_forced(db_session, monkeypatch):
    # inject FakeIntakeClassifier(needs_reply=0) and rng that always picks max ignore
    ...

@pytest.mark.asyncio
async def test_decide_delivery_blocks_voice_on_url():
    ...
```

For service tests, publish via `InMemoryProducer` and assert event fields, or call service methods and inspect return + `producer.publish` mock.

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement classifier, service, handlers, register in `main.py` `_register_bus_handlers` after memory, before orchestrator.**

- [ ] **Step 4: Run**

Run: `pytest tests/modules/behavior/test_classifier.py tests/modules/behavior/test_service.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/modules/behavior src/main.py tests/modules/behavior
git commit -m "feat(behavior): intake/delivery service and bus handlers"
```

---

### Task 5: Telegram send_voice and chat action

**Files:**
- Modify: `src/modules/telegram_clients/adapters/client_manager.py`
- Modify: `src/modules/telegram_clients/handlers.py`
- Modify: `src/modules/telegram_clients/schemas/events.py` (`TgMessageSent` add optional `message_type: str = "text"`)
- Test: `tests/modules/telegram_clients/test_send_voice.py` (or extend existing client_manager tests)

**Interfaces:**
- Consumes: `BusTopics.TG_MESSAGE_SEND_VOICE`
- Produces:

```python
async def send_chat_action(self, account_id: UUID, chat_id: int, action: str = "record_audio") -> None:
    """client.send_chat_action. Missing client → raise NotFoundError. Swallow is NOT here; orchestrator ignores errors."""

async def send_voice(self, account_id: UUID, chat_id: int, path: Path) -> None:
    """Telethon send_file(chat_id, file=str(path), voice_note=True). Missing client → NotFoundError."""
```

Handler `handle_send_voice`: payload `account_id`, `chat_id`, `path`, optional `text` (transcript for `TgMessageSent`). Call `send_voice`, then `TgMessageSent(..., text=text or "", message_type="voice", success=...)`. Do not unlink the file in the handler (orchestrator unlinks after publish, or handler unlinks in `finally` after send — **handler unlinks in `finally`** so TTS temp files do not leak if orchestrator dies). Spec: orchestrator unlinks; pick **handler `finally: Path(path).unlink(missing_ok=True)`** after send attempt.

- [ ] **Step 1: Failing test** with `AsyncMock` client on manager: `send_voice` calls `send_file(..., voice_note=True)`; handler publishes `TG_MESSAGE_SENT` with `message_type=voice`.

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement methods + handler subscription.**

- [ ] **Step 4: Run tests PASS**

- [ ] **Step 5: Commit**

```bash
git add src/modules/telegram_clients tests/modules/telegram_clients
git commit -m "feat(telegram): send_voice command and record_audio action"
```

---

### Task 6: Orchestrator wiring + reply emotion strip

**Files:**
- Modify: `src/modules/orchestrator/schemas/state.py`
- Modify: `src/modules/orchestrator/service.py`
- Modify: `src/modules/llm/prompts/reply.md`
- Modify: `tests/modules/orchestrator/test_orchestrator_service.py`
- Modify: `tests/modules/orchestrator/test_pipeline.py`
- Test: add cases in those files

**Interfaces:**
- Consumes: behavior events, TTS events, `TG_MESSAGE_SEND_VOICE`
- Produces: updated pipeline

`OrchestratorState` add:

```python
batch_messages: list = Field(default_factory=list)
asked_voice: int = 0
pending_outgoing_texts: list[str] = Field(default_factory=list)
pending_delivery: str | None = None  # text | voice
```

On `MEMORY_BATCH_PROCESSED` / `MEMORY_CONTEXT_BUILT`: keep `batch_messages` from payload (`payload.get("messages")` on processed; on context built, keep existing state list). On `MEMORY_CONTEXT_BUILT` publish `BEHAVIOR_DECIDE_INTAKE` with `context`, `batch_messages`, ids — **do not** publish `LLM_GENERATE_REPLY` here.

On `BEHAVIOR_INTAKE_DECIDED`:
- `ignore` → `self._states.pop(...)`; return
- `respond` → save `asked_voice` on state; publish `LLM_GENERATE_REPLY` as today

On `LLM_REPLY_GENERATED`: publish `BEHAVIOR_DECIDE_DELIVERY` with outgoing messages, `state.batch_messages`, `state.asked_voice`. Do not send yet.

On `BEHAVIOR_DELIVERY_DECIDED`:
- `text`: existing send loop; set `pending_delivery="text"`
- `voice`: try `publish` is not chat action — orchestrator cannot call manager. **Chat action:** add `BusTopics.TG_CHAT_ACTION = "telegram_clients.command.chat_action"` in Task 5 if missing; if Task 5 only added manager method, add command+handler here:

Payload `{account_id, chat_id, action: "record_audio"}`. Handler calls `send_chat_action`, logs errors, no event required.

Then `await asyncio.sleep(random.uniform(1.0, 1.5))` — in tests monkeypatch `asyncio.sleep`. Publish `TTS_SYNTHESIZE` with joined text (`". ".join(texts)`). Store `pending_outgoing_texts` and `pending_delivery="voice"`.

On `TTS_SYNTHESIZED`: publish `TG_MESSAGE_SEND_VOICE` with `path`, `text` (joined pending). On `TTS_SYNTHESIZE_SKIPPED`: publish `TG_MESSAGE_SEND` for each pending text (fallback). Clear pending after scheduling send.

On `TG_MESSAGE_SENT`: existing memory update; also publish `BEHAVIOR_NOTE_DELIVERY` with `channel` from `payload.get("message_type")` if `voice` else `text`. If TTS fallback sent text, channel is `text` (resets streak). If `success=False` and channel was voice, still `note_delivery` with `voice` so streak counts attempt — **spec says increment after successful voice**. So only `note_delivery` when `success` is true.

`reply.md` append:

```
If the last line of your output is a JSON object {"emotion": 0} or {"emotion": 1}, that line is stripped and never shown to the user. Use 1 only if the reply is vividly emotional. Omitting the line is fine.
```

Do not mention ignore/voice actions in the prompt.

Update `test_orchestrator_service.py`: after context built, expect `BEHAVIOR_DECIDE_INTAKE` not `LLM_GENERATE_REPLY`. Simulate `intake_decided` respond, then existing generate. After `LLM_REPLY_GENERATED`, expect `DECIDE_DELIVERY` not send. Simulate `delivery_decided` text, then send.

Add tests:
- ignore → no `LLM_GENERATE_REPLY`
- delivery voice → `TTS_SYNTHESIZE`, not `TG_MESSAGE_SEND`
- `TTS_SYNTHESIZE_SKIPPED` → `TG_MESSAGE_SEND`

Pipeline e2e `test_incoming_message_reaches_telegram_send`: register behavior handlers with `FakeIntakeClassifier` and monkeypatch `create_async_session` like memory. After context, auto-intake: either drain full bus (behavior will run if DB works) or inject a subscriber that auto-responds. **Preferred:** register real behavior handlers + fake classifier `needs_reply=1` + `db_session` patch on behavior handlers too, and monkeypatch `softmax_sample` to always return `respond` / `text` so the e2e stays deterministic.

Monkeypatch:

```python
from src.modules.behavior.engine import Decision

def _fixed_decide(policy, ctx, rng, temperature=None):
    action = "respond" if policy.fallback == "respond" else "text"
    scores = {a: 1.0 for a in policy.legal_actions}
    return Decision(action=action, scores=scores, blocked={})

monkeypatch.setattr("src.modules.behavior.service.decide", _fixed_decide)
```

- [ ] **Step 1: Write failing orchestrator tests** (update existing assertions first so they fail for the right reason).

- [ ] **Step 2: Run** `pytest tests/modules/orchestrator/ -v` — FAIL

- [ ] **Step 3: Implement orchestrator + prompt + chat_action command if not in Task 5.**

- [ ] **Step 4: Run** `pytest tests/modules/orchestrator/ tests/modules/behavior/ -v` — PASS

- [ ] **Step 5: Commit**

```bash
git add src/modules/orchestrator src/modules/llm/prompts/reply.md src/modules/telegram_clients src/core/bus_topics.py tests/modules/orchestrator
git commit -m "feat(orchestrator): route intake, delivery, and TTS voice with text fallback"
```

---

### Task 7: Full pipeline regression

**Files:**
- Modify: `tests/modules/orchestrator/test_pipeline.py` (register behavior + tts stubs)
- Test: add `test_ignore_does_not_send`, `test_voice_delivery_uses_tts`

**Interfaces:** none new.

Register `register_tts` with stub provider (already skips). Register behavior. Patch behavior `create_async_session`. Force softmax as in Task 6 for the happy-path send test.

New test: classifier `needs_reply=0` and softmax returns `ignore` if present else first key — assert `send_message` not called.

New test: softmax returns `voice` for delivery weights; assert `send_message` not called and TTS skip leads to `send_message` (stub TTS always skips → this asserts fallback). To test real voice send, mock TTS to publish `synthesized` with a temp path and assert `send_voice`.

```python
@pytest.mark.asyncio
async def test_tts_skip_falls_back_to_text(db_session, monkeypatch, tmp_path):
    ...
```

- [ ] **Step 1: Write the two extra pipeline tests**

- [ ] **Step 2: Run — FAIL if wiring incomplete**

- [ ] **Step 3: Fix gaps only (no new features)**

- [ ] **Step 4: Run** `pytest tests/modules/orchestrator/ tests/modules/behavior/ tests/modules/tts/ tests/modules/telegram_clients/ -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/modules/orchestrator/test_pipeline.py
git commit -m "test(behavior): pipeline ignore, voice TTS, and text fallback"
```

---

## Spec coverage (self-review)

| Spec item | Task |
|-----------|------|
| decide_intake before LLM | 6 |
| ignore skips LLM, memory already stored | 6, 7 |
| decide_delivery after reply | 6 |
| pluggable Policy / Criterion / Filter | 2 |
| hard filters | 2 |
| objective / life / mood deltas | 2 |
| intake JSON + fail-open | 4 |
| emotion heuristic + suffix | 2, 6 |
| want-speak from activity | 2 |
| softmax + noise | 2 |
| life per account, lazy 2–4h | 3 |
| chat streak + note_delivery | 3, 4, 6 |
| send_voice + record + 1–1.5s | 5, 6 |
| TTS skip → text | 6, 7 |
| no delay/sticker winners | 2 (not in sample keys) |
| config timezone/temp/timeout | 1 |
| voice send fail no double text | 6 (no fallback on send_voice failure) |
| missing account_id fail-open | 4 |
