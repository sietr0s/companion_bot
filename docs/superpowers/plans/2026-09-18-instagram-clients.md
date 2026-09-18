# Instagram clients Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `instagram_clients` (instagrapi) as a Direct DM companion channel, with channel-aware `ChatRef` and `User(platform, platform_user_id)` replacing `telegram_id`.

**Architecture:** Thick module copied from `telegram_clients`. Own bus topics and HTTP. `InstagramClientManager` holds sync `instagrapi.Client` instances, runs them in a thread pool, polls Direct inbox, serializes calls per account. Orchestrator subscribes to both TG and IG received events and publishes `send_message` to the topic matching `chat.channel`. Instagram delivery never uses TTS.

**Tech Stack:** FastAPI, SQLAlchemy + Alembic, in-memory/Kafka bus, instagrapi, pytest-asyncio, existing frontend OpenAPI generator.

**Spec:** `docs/superpowers/specs/2026-09-18-instagram-clients-design.md`

## Global Constraints

- Copy ADR 0001 thick-module layout from `telegram_clients`; do not create a shared `messaging` package.
- Do not publish Instagram events onto `telegram_clients.*` topics.
- Password is never stored; session is `Client.get_settings()` JSON at `sessions/instagram/{account_id}.json`.
- instagrapi is sync: `asyncio.to_thread` (or executor). One `asyncio.Lock` per account.
- Poll inbox only; do not auto-approve pending Direct requests.
- v1 send is text only; no `send_voice` / `chat_action` topics for Instagram.
- `ChatRef.channel` is required; missing channel is an error, not a telegram default.
- `user.telegram_id` is dropped in one Alembic revision after backfill.
- Tests never call live Instagram; inject a fake Client.
- `datetime.now(UTC)` in app code.
- `get_instagram_client_manager()` without `configure_*` raises `RuntimeError`.
- New HTTP schemas use `Instagram*` prefixes (`InstagramAccountCreate` / `Update` / `Read`).

## File map

| File | Responsibility |
|------|----------------|
| `src/domain/chat.py` | channel-aware `ChatRef`, `outgoing_batch` |
| `src/modules/users/models.py` | `platform` + `platform_user_id` |
| `src/modules/users/repository.py` | `get_by_platform` |
| `src/modules/users/service.py` | `get_or_create_from_platform` |
| `src/modules/users/schemas/public.py` | HTTP without `telegram_id` |
| `src/modules/users/schemas/events.py` | `platform`, `platform_user_id` |
| `alembic/versions/20260918_user_platform_instagram.py` | user columns + IG tables |
| `src/core/bus_topics.py` | `IG_*` topics |
| `src/core/container.py` | `InstagramClientManager` |
| `src/core/database.py` | import IG models |
| `src/main.py` | router, handlers, restore/poll, shutdown |
| `src/modules/orchestrator/service.py` | IG received, send by channel, state key includes channel |
| `src/modules/behavior/filters.py` | block voice when `channel=instagram` |
| `src/modules/instagram_clients/**` | new module |
| `frontend/src/pages/instagram/*` | accounts / login / whitelist UI |
| `requirements.txt` | `instagrapi` |

---

### Task 1: Channel-aware ChatRef

**Files:**
- Modify: `src/domain/chat.py`
- Modify: `tests/domain/test_chat.py`
- Modify: every constructor/test that builds `ChatRef`/`Batch`/`outgoing_batch` with `telegram_chat_id` (grep `telegram_chat_id` and fix in this task for **domain tests first**, remaining modules in Task 2)

**Interfaces:**
- Produces:

```python
from typing import Literal

Channel = Literal["telegram", "instagram"]

class ChatRef(BaseModel):
    channel: Channel
    account_id: UUID | None = None
    chat_id: int
    conversation_id: UUID | None = None

    def state_key(self) -> tuple[str, str, int]:
        return (self.channel, str(self.account_id) if self.account_id else "", int(self.chat_id))

    def bus_ids(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "account_id": str(self.account_id) if self.account_id else None,
            "chat_id": self.chat_id,
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            # keep aliases so in-flight TG payloads still parse during Task 2:
            "telegram_account_id": str(self.account_id) if self.account_id else None,
            "telegram_chat_id": self.chat_id,
        }

    def adapter_ids(self) -> dict[str, Any]:
        return {
            "account_id": str(self.account_id) if self.account_id else None,
            "chat_id": self.chat_id,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ChatRef: ...

def outgoing_batch(*, channel: Channel, account_id: UUID | None, chat_id: int, text: str) -> Batch: ...
```

- `from_payload` **requires** `channel`. `chat_id` from `chat_id` or `telegram_chat_id`. `account_id` from `account_id` or `telegram_account_id`.
- `merged` prefers `other` for set fields; `channel` must match or take `other.channel` if self is being filled from payload.

- [ ] **Step 1: Write the failing tests**

In `tests/domain/test_chat.py` replace ChatRef tests:

```python
def test_chat_ref_from_payload_requires_channel():
    aid = uuid4()
    ref = ChatRef.from_payload({"channel": "telegram", "account_id": aid, "chat_id": 9})
    assert ref.channel == "telegram"
    assert ref.chat_id == 9
    assert ref.adapter_ids()["chat_id"] == 9
    try:
        ChatRef.from_payload({"account_id": aid, "chat_id": 9})
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_outgoing_batch_builds_messages():
    batch = outgoing_batch(channel="telegram", chat_id=7, account_id=uuid4(), text="a<next_message>b")
    assert batch.channel == "telegram"
    assert [m.text for m in batch.messages] == ["a", "b"]
```

Update `Batch(...)` literals in this file to `channel="telegram", chat_id=1, account_id=...`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/domain/test_chat.py -v`

Expected: FAIL (`channel` unexpected / `telegram_chat_id` required)

- [ ] **Step 3: Implement ChatRef**

Replace fields on `ChatRef` as in Interfaces. Update `Batch` (inherits ChatRef). Update `outgoing_batch`. Keep `Message.telegram_message_id` as-is (TG-specific message id; IG can leave it None).

- [ ] **Step 4: Run tests**

Run: `pytest tests/domain/test_chat.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/chat.py tests/domain/test_chat.py
git commit -m "feat(domain): channel-aware ChatRef"
```

---

### Task 2: Propagate ChatRef through pipeline (Telegram still works)

**Files:**
- Modify: `src/modules/batching/service.py`, `src/modules/batching/schemas/events.py` (and models if they store `telegram_chat_id` — keep DB column name `telegram_chat_id` **or** rename to `chat_id` + add `channel`; prefer add `channel` string column default `'telegram'` and keep `telegram_chat_id` as the numeric chat id to avoid a memory rewrite. Spec is ChatRef-level; batching persistence may keep historical column names mapped in code.)
- Modify: `src/modules/orchestrator/service.py` — `_state_key` includes channel; `_state_for(channel, account_id, chat_id)`; all `telegram_chat_id` payload reads go through `ChatRef.from_payload`; `_on_telegram_message` sets `channel=telegram` when merging if payload lacks it **only if** TG events are updated to include channel (preferred: update TG event payloads).
- Modify: `src/modules/telegram_clients/schemas/events.py` — add `channel: Literal["telegram"] = "telegram"` on received/sent if needed; send command payloads include `channel`.
- Modify: `src/modules/telegram_clients/handlers.py` — include `channel: "telegram"` in published dicts / ChatRef construction.
- Modify: memory/llm/behavior event payloads that copy `bus_ids()`.
- Modify: tests that construct `ChatRef`/`Batch`/`UserCreate` wait — users are Task 3. Fix ChatRef tests across `tests/modules/**`, `tests/bus/**`.

**Interfaces:**
- Consumes: `ChatRef` from Task 1
- Produces: orchestrator state keyed by `(channel, account_id, chat_id)`; TG path always `channel="telegram"`

Orchestrator delivery (text) stays on `BusTopics.TG_MESSAGE_SEND` in this task (IG topic comes in Task 9). Helper:

```python
def _send_text_topic(channel: str) -> str:
    if channel == "instagram":
        return BusTopics.IG_MESSAGE_SEND  # added in Task 6; until then only telegram
    return BusTopics.TG_MESSAGE_SEND
```

In this task, if `IG_MESSAGE_SEND` is not defined yet, only publish TG and assert tests still pass for telegram. Add the helper in Task 9.

- [ ] **Step 1: Write/adjust failing tests**

Update `tests/domain` already done. Fix `tests/modules/orchestrator/test_pipeline.py` and `test_orchestrator_service.py` to pass `channel="telegram"` in payloads and ChatRef.

Add:

```python
def test_state_key_includes_channel():
    # same numeric chat_id on two channels must not share OrchestratorState
    ...
```

If too heavy for orchestrator internals, test `ChatRef.state_key()` distinction only (already Task 1) and in orchestrator test two received events (skip until IG exists). For this task: update existing orchestrator tests so they fail on missing `channel` then pass.

- [ ] **Step 2: Run a focused failing set**

Run: `pytest tests/modules/orchestrator tests/modules/batching tests/domain -q`

Expected: FAIL on ChatRef validation / missing fields

- [ ] **Step 3: Update producers and consumers**

Every `ChatRef(telegram_chat_id=...)` → `ChatRef(channel="telegram", chat_id=..., account_id=...)`.

`from_payload` already maps aliases. **TG publish dicts must include `"channel": "telegram"`.**

Orchestrator `_state_key`:

```python
@staticmethod
def _state_key(channel: str, account_id: UUID | str | None, chat_id: int) -> tuple[str, str, int]:
    return (channel, str(account_id) if account_id else "", int(chat_id))
```

When reading a payload, `ref = ChatRef.from_payload(payload)` then `self._states[ref.state_key()]`.

Batching command schemas: add `channel: Literal["telegram", "instagram"] = "telegram"` so old tests can set it; prefer required field and update tests.

- [ ] **Step 4: Run tests**

Run: `pytest tests/modules/orchestrator tests/modules/batching tests/modules/telegram_clients tests/modules/behavior tests/modules/memory tests/modules/llm tests/domain -q`

Expected: PASS (users tests still old until Task 3)

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat(chat): propagate ChatRef.channel through telegram pipeline"
```

---

### Task 3: User platform identity (drop telegram_id)

**Files:**
- Modify: `src/modules/users/models.py`
- Modify: `src/modules/users/repository.py`
- Modify: `src/modules/users/service.py`
- Modify: `src/modules/users/schemas/public.py`
- Modify: `src/modules/users/schemas/events.py`
- Modify: `tests/modules/users/**`, `tests/base/test_repository.py`, `tests/bus/test_message_bus.py`
- Create: `alembic/versions/20260918_user_platform_instagram.py` (user part now; IG tables in same file in Task 4 — **put both in this revision file but only user ops if you split**; spec says one revision for user drop. Combine user + IG tables in **one** alembic file created here, IG `create_table` added in Task 4 in the same revision if not merged yet. Simpler: create the revision in Task 4 with both. This task: models + tests using `create_all` in pytest.)

**Interfaces:**
- Produces:

```python
class User(BaseModel):
    platform: Mapped[str]  # "telegram" | "instagram"
    platform_user_id: Mapped[str]
    username: Mapped[str | None]
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    notes: Mapped[str | None]
    # UniqueConstraint("platform", "platform_user_id")

class UserRepository:
    async def get_by_platform(self, session, platform: str, platform_user_id: str) -> User | None: ...

class UserService:
    async def get_or_create_from_platform(
        self, session, *, platform: str, platform_user_id: str,
        username: str | None = None, first_name: str | None = None, last_name: str | None = None,
    ) -> User: ...
```

Remove `get_or_create_from_telegram` and `get_by_telegram_id`.

Events:

```python
class UserCreated(BaseEvent):
    user_id: UUID
    platform: str
    platform_user_id: str
```

- [ ] **Step 1: Failing tests**

Rewrite `tests/modules/users/test_user_service.py`:

```python
async def test_get_or_create_from_platform_creates(db_session, user_service):
    user = await user_service.get_or_create_from_platform(
        db_session, platform="telegram", platform_user_id="42", first_name="Alice"
    )
    assert user.platform == "telegram"
    assert user.platform_user_id == "42"

async def test_instagram_and_telegram_same_numeric_id_are_distinct(db_session, user_service):
    a = await user_service.get_or_create_from_platform(
        db_session, platform="telegram", platform_user_id="1"
    )
    b = await user_service.get_or_create_from_platform(
        db_session, platform="instagram", platform_user_id="1"
    )
    assert a.id != b.id
```

HTTP integration: POST `{"platform":"telegram","platform_user_id":"10001","first_name":"Alice"}`.

- [ ] **Step 2: Run tests — expect fail**

Run: `pytest tests/modules/users tests/base/test_repository.py tests/bus/test_message_bus.py -v`

- [ ] **Step 3: Implement model/service/schemas**

`platform_user_id` is `String(64)`, not BigInteger.

Grep `telegram_id` in `src/modules/users` and telegram handlers that call `get_or_create_from_telegram` — switch those call sites:

```python
await user_service.get_or_create_from_platform(
    session,
    platform="telegram",
    platform_user_id=str(sender_id),
    ...
)
```

- [ ] **Step 4: Tests pass**

Run: `pytest tests/modules/users tests/base/test_repository.py tests/bus/test_message_bus.py tests/modules/telegram_clients -q`

- [ ] **Step 5: Commit**

```bash
git add src/modules/users tests
git commit -m "feat(users): identify people by platform and platform_user_id"
```

---

### Task 4: Instagram persistence + Alembic

**Files:**
- Create: `src/modules/instagram_clients/__init__.py`
- Create: `src/modules/instagram_clients/models.py`
- Create: `src/modules/instagram_clients/repository.py`
- Create: `src/modules/instagram_clients/exceptions.py` (re-export AppException types as needed)
- Create: `src/modules/instagram_clients/config.py` — `INSTAGRAM_POLL_INTERVAL_S: float = 20`, `INSTAGRAM_SESSION_DIR: str = "sessions/instagram"`
- Modify: `src/core/database.py` `_load_models`
- Modify: `alembic/env.py` if it imports models
- Create: `alembic/versions/20260918_user_platform_instagram.py`
- Test: `tests/modules/instagram_clients/test_repository.py`

**Interfaces:**
- Produces models:

```python
class InstagramAccount(BaseModel):
    __tablename__ = "instagram_account"
    id: Mapped[uuid.UUID]  # PK default uuid4
    username: Mapped[str]
    instagram_pk: Mapped[int | None]  # BigInteger
    session_file: Mapped[str]
    is_connected: Mapped[bool]
    full_name: Mapped[str | None]

class InstagramSettings(BaseModel):
    __tablename__ = "instagram_settings"
    account_id: FK cascade
    use_whitelist: Mapped[bool]  # default True
    whitelist_user_pks: Mapped[list | None]  # JSON, default list

class InstagramChatState(BaseModel):
    __tablename__ = "instagram_chat_state"
    account_id: FK cascade
    thread_id: Mapped[int]  # BigInteger
    last_item_id: Mapped[str]  # String(64)
    UniqueConstraint("account_id", "thread_id")
```

Alembic `upgrade`:
1. `user`: add `platform` (nullable), `platform_user_id` (nullable)
2. backfill: `platform='telegram'`, `platform_user_id = telegram_id::text`
3. alter not null; unique `(platform, platform_user_id)`; drop unique/index on `telegram_id`; drop column `telegram_id`
4. `create_table` for the three IG tables

SQLite tests use metadata create_all — still implement explicit alembic for postgres.

- [ ] **Step 1: Failing repository test**

```python
async def test_create_account_and_settings(db_session):
    repo = InstagramAccountRepository()
    acc = await repo.create(db_session, {
        "username": "bot",
        "session_file": "sessions/instagram/x.json",
        "is_connected": False,
    })
    assert acc.id is not None
    assert acc.instagram_pk is None
```

- [ ] **Step 2: Run — fail on import**

Run: `pytest tests/modules/instagram_clients/test_repository.py -v`

- [ ] **Step 3: Models + repositories + alembic + database.py import**

Repositories: `InstagramAccountRepository`, `InstagramSettingsRepository`, `InstagramChatStateRepository` with `get_by_account_id`, `get_state(account_id, thread_id)`, `upsert_last_item_id`.

- [ ] **Step 4: Tests pass**

Run: `pytest tests/modules/instagram_clients/test_repository.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/modules/instagram_clients src/core/database.py alembic
git commit -m "feat(instagram): account, settings, chat_state tables"
```

---

### Task 5: Instagram HTTP CRUD (no live Client)

**Files:**
- Create: `src/modules/instagram_clients/schemas/public.py`
- Create: `src/modules/instagram_clients/services/account.py` (DB only this task)
- Create: `src/modules/instagram_clients/services/settings.py`
- Create: `src/modules/instagram_clients/services/chat_state.py`
- Create: `src/modules/instagram_clients/services/__init__.py`
- Create: `src/modules/instagram_clients/dependencies.py` (repos + services; manager configure stub)
- Create: `src/modules/instagram_clients/routers/public.py` and `public_accounts.py`, `public_settings.py`, `public_whitelist.py`, `public_auth.py` (auth routes can 501 until Task 7 — **do not 501**: add login routes in Task 7. This task: accounts CRUD, settings, whitelist.)
- Modify: `src/main.py` include `instagram` public_router
- Test: `tests/modules/instagram_clients/test_http.py`

**Interfaces:**
- HTTP prefix `/api/v1/public/instagram`, admin dependency like telegram
- Schemas: `InstagramAccountCreate` (`username: str`), `InstagramAccountUpdate`, `InstagramAccountRead` (no password)
- Create account sets `session_file` to `{INSTAGRAM_SESSION_DIR}/{id}.json` (id known after insert: update path after create)
- Whitelist: `POST /{account_id}/whitelist` body `{user_pk: int}`, `DELETE /{account_id}/whitelist/{user_pk}`

- [ ] **Step 1: Failing HTTP test**

Mirror `tests/modules/telegram_clients/test_settings_integration.py` auth headers.

```python
async def test_create_account(client, admin_headers):
    r = await client.post("/api/v1/public/instagram/accounts", json={"username": "x"}, headers=admin_headers)
    assert r.status_code in (200, 201)
    body = r.json()
    assert body["username"] == "x"
    assert "password" not in body
    assert body["is_connected"] is False
```

- [ ] **Step 2: Run fail**

Run: `pytest tests/modules/instagram_clients/test_http.py -v`

- [ ] **Step 3: Implement routers/services, mount in main.py**

`create_account` does not login.

- [ ] **Step 4: Tests pass**

Run: `pytest tests/modules/instagram_clients/test_http.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/modules/instagram_clients src/main.py tests/modules/instagram_clients
git commit -m "feat(instagram): public HTTP for accounts and whitelist"
```

---

### Task 6: Bus topics + event schemas + manager skeleton + DI

**Files:**
- Modify: `src/core/bus_topics.py`
- Create: `src/modules/instagram_clients/schemas/events.py`
- Create: `src/modules/instagram_clients/adapters/__init__.py`
- Create: `src/modules/instagram_clients/adapters/client_manager.py`
- Create: `src/modules/instagram_clients/adapters/fake_client.py` (test double used in unit tests; production uses instagrapi)
- Modify: `src/modules/instagram_clients/dependencies.py`
- Modify: `src/core/container.py`
- Modify: `requirements.txt` add `instagrapi>=2.0.0` (pin whatever `pip index` allows; import `from instagrapi import Client`)
- Test: `tests/modules/instagram_clients/test_manager.py`, `tests/test_dependencies.py`

**Interfaces:**
- Produces:

```python
# BusTopics
IG_MESSAGE_RECEIVED = "instagram_clients.event.message.received"
IG_MESSAGE_SENT = "instagram_clients.event.message.sent"
IG_ACCOUNT_CONNECTED = "instagram_clients.event.account.connected"
IG_ACCOUNT_DISCONNECTED = "instagram_clients.event.account.disconnected"
IG_MESSAGE_SEND = "instagram_clients.command.send_message"

class IgMessageReceived(BaseEvent):
    event_name: str = BusTopics.IG_MESSAGE_RECEIVED
    account_id: UUID
    chat_id: int
    message_id: str
    sender: Person
    text: str | None = None
    media: list = Field(default_factory=list)
    channel: Literal["instagram"] = "instagram"

class InstagramClientManager:
    def __init__(self, client_factory=None) -> None: ...
    def configure_lock(self, account_id: UUID) -> asyncio.Lock: ...
    async def send_text(self, account_id: UUID, thread_id: int, text: str) -> str: ...  # returns item id
    async def stop_all(self) -> None: ...
```

`client_factory` default `lambda: Client()` so tests pass `lambda: FakeInstagramClient()`.

`get_instagram_client_manager()` RuntimeError without configure — add test next to telegram manager tests in `tests/test_dependencies.py`.

- [ ] **Step 1: Failing tests**

```python
def test_get_instagram_client_manager_without_configure():
    # reset module global if test isolation allows
    with pytest.raises(RuntimeError):
        get_instagram_client_manager()

@pytest.mark.asyncio
async def test_manager_send_text_uses_fake():
    fake = FakeInstagramClient()
    mgr = InstagramClientManager(client_factory=lambda: fake)
    # attach pre-made client
    aid = uuid4()
    mgr._clients[aid] = fake
    item_id = await mgr.send_text(aid, thread_id=11, text="hi")
    assert item_id
    assert fake.sent[-1] == (11, "hi")
```

- [ ] **Step 2: Run fail**

Run: `pytest tests/modules/instagram_clients/test_manager.py tests/test_dependencies.py -v`

- [ ] **Step 3: Implement**

`FakeInstagramClient`: attributes `pk`, `sent: list`, methods `login`, `login_by_sessionid`, `dump_settings`, `set_settings`, `direct_threads`, `direct_send`, `account_info`. Raise `TwoFactorRequired` / `ChallengeRequired` from a flag.

Manager `send_text`: `async with self._locks[account_id]: return await asyncio.to_thread(...)`.

Do not start poll yet.

- [ ] **Step 4: Tests pass**

- [ ] **Step 5: Commit**

```bash
git add src/core/bus_topics.py src/core/container.py src/modules/instagram_clients requirements.txt tests
git commit -m "feat(instagram): client manager skeleton and bus topics"
```

---

### Task 7: Login, 2FA, challenge, session dump

**Files:**
- Create: `src/modules/instagram_clients/adapters/login.py`
- Modify: `src/modules/instagram_clients/services/account.py` — coordinate DB + manager
- Modify: `src/modules/instagram_clients/routers/public_auth.py`
- Modify: `src/modules/instagram_clients/exceptions.py` — `InstagramLoginChallengeError` (ConflictError, extra `login_state`)
- Test: `tests/modules/instagram_clients/test_login.py`

**Interfaces:**
- `POST /api/v1/public/instagram/accounts/{id}/login` body `InstagramLoginRequest(username, password)`
- `POST .../two-factor` body `{code: str}`
- `POST .../challenge` body `{code: str}`
- Success: dump settings to `account.session_file`, set `instagram_pk`, `is_connected=True`, publish `IG_ACCOUNT_CONNECTED`
- 2FA: HTTP 409, `detail` may be string; put `login_state` in a structured `ConflictError` subclass:

```python
class InstagramTwoFactorRequired(ConflictError):
    def __init__(self):
        super().__init__("two_factor_required")
        self.login_state = "two_factor"
```

If `AppException` only has `detail` string, use detail `"two_factor_required"` / `"challenge_required"` and document that the frontend keys off `detail`. Do not invent a new HTTP envelope.

Keep pending Client in `manager._pending_login[account_id]` until 2FA completes.

- [ ] **Step 1: Failing tests with FakeInstagramClient**

```python
@pytest.mark.asyncio
async def test_login_success_dumps_settings(tmp_path):
    ...

@pytest.mark.asyncio
async def test_login_two_factor_then_code():
    fake.require_2fa = True
    ...
```

- [ ] **Step 2: Run fail**

- [ ] **Step 3: Implement login adapter + auth routes**

Never write password to DB or session JSON beyond what instagrapi `get_settings()` already contains.

- [ ] **Step 4: Tests pass**

Run: `pytest tests/modules/instagram_clients/test_login.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/modules/instagram_clients tests/modules/instagram_clients
git commit -m "feat(instagram): login, 2FA, and session dump"
```

---

### Task 8: Poll Direct inbox → received events

**Files:**
- Modify: `src/modules/instagram_clients/adapters/client_manager.py` — `start_poll`, `stop_poll`, `_poll_once`
- Modify: `src/modules/instagram_clients/services/account.py` — after connect, start poll; `restore_sessions`
- Create: `src/modules/instagram_clients/handlers.py` — send command (Task 9) can wait; this task may only start loops
- Test: `tests/modules/instagram_clients/test_poll.py`

**Interfaces:**

```python
class InstagramClientManager:
    async def start_poll(self, account_id: UUID, *, own_pk: int, producer, chat_state_service, settings) -> None: ...
    async def stop_poll(self, account_id: UUID) -> None: ...
    async def poll_once(...) -> list[IgMessageReceived]: ...  # testable without sleep
```

`poll_once` rules:
- `direct_threads()` inbox only
- skip items where `user_id == own_pk`
- skip if `use_whitelist` and sender pk not in `whitelist_user_pks` (empty list → skip all)
- skip `item_id <= last_item_id` (string compare only if both numeric: compare as int when `isdigit()`, else skip exact id equality and treat unknown as new — **prefer integer compare when both look like ints**)
- persist last_item_id via chat_state service
- emit `IgMessageReceived` with `channel="instagram"`, `chat_id=thread_id`, `message_id=str(item_id)`, `sender.sender_id=user_pk`

On challenge/rate limit during poll: `is_connected=False`, publish disconnected, stop task. Do not tight-loop login.

Interval: `instagram_settings.INSTAGRAM_POLL_INTERVAL_S` + jitter `random.uniform(0, 3)`.

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.asyncio
async def test_poll_once_emits_new_text_skips_own_and_old(fake, producer):
    ...

@pytest.mark.asyncio
async def test_poll_once_respects_whitelist():
    ...
```

- [ ] **Step 2: Run fail**

- [ ] **Step 3: Implement poll_once + loop**

- [ ] **Step 4: Tests pass**

Run: `pytest tests/modules/instagram_clients/test_poll.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/modules/instagram_clients tests/modules/instagram_clients
git commit -m "feat(instagram): poll Direct inbox into bus events"
```

---

### Task 9: Send command, orchestrator IG path, behavior voice block

**Files:**
- Create/modify: `src/modules/instagram_clients/handlers.py` — subscribe `IG_MESSAGE_SEND`
- Modify: `src/modules/orchestrator/service.py` — subscribe `IG_MESSAGE_RECEIVED` (same handler as TG but skip STT: no voice types in v1); `_send_text_topic(channel)`; do not call `_deliver_voice` when `channel==instagram` even if action is voice (defense in depth)
- Modify: `src/modules/behavior/filters.py` — `InstagramVoiceFilter`
- Modify: `src/modules/behavior/policies.py` or wherever filters are attached — append the filter
- Modify: `src/modules/behavior/engine.py` `DecisionContext` — `channel: str = "telegram"`
- Modify: `src/modules/behavior/service.py` — copy `channel` from ChatRef into context
- Modify: `src/main.py` — `register_ig_handlers`
- Test: `tests/modules/instagram_clients/test_send.py`, `tests/modules/behavior/test_filters.py` or new `test_instagram_voice.py`, orchestrator test that IG received without STT publishes batch add

**Interfaces:**

```python
class InstagramChannelVoiceFilter:
    name = "instagram_voice"
    def blocked(self, ctx: DecisionContext) -> dict[str, str]:
        if getattr(ctx, "channel", "telegram") == "instagram":
            return {"voice": "instagram"}
        return {}
```

Orchestrator `on_delivery_decided`:

```python
topic = BusTopics.IG_MESSAGE_SEND if state.chat.channel == "instagram" else BusTopics.TG_MESSAGE_SEND
if action == "voice" and state.chat.channel == "instagram":
    action = "text"
if action == "voice":
    self._spawn(self._deliver_voice(...))
    return
for text in texts:
    await self._producer.publish(topic, {**ids, "text": text})
```

IG received handler: if no text, return (no STT). Else merge ChatRef with `channel=instagram` and `BATCH_ADD_MESSAGE` as today.

Users upsert: orchestrator or a small IG handler before batching? Telegram currently upserts where? Grep `get_or_create`. If telegram does it in telegram module before publish received, do the same in IG poll after whitelist: `get_or_create_from_platform(platform="instagram", platform_user_id=str(pk), ...)`.

- [ ] **Step 1: Failing tests** for filter, send handler, orchestrator skip STT

- [ ] **Step 2: Run fail**

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run**

Run: `pytest tests/modules/instagram_clients tests/modules/behavior tests/modules/orchestrator -q`

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat(instagram): send path and pipeline wiring"
```

---

### Task 10: Lifespan restore + frontend

**Files:**
- Modify: `src/main.py` lifespan — `restore_ig_sessions` then start poll for `is_connected`; `stop_all` on IG manager at shutdown
- Modify: `src/core/container.py` already has manager
- Frontend: copy telegram accounts page patterns
  - `frontend/src/pages/instagram/InstagramAccountsPage.tsx`
  - login modal with password + 2FA field if `detail === "two_factor_required"`
  - whitelist on settings subpage or same page
- Modify: `frontend/src/router.tsx`, layout nav
- Run: `python scripts/generate_frontend_openapi.py` then `npm run generate:api` in `frontend/`
- Test: `tests/test_frontend_openapi.py` if it asserts telegram paths — add instagram prefix presence
- Modify: `README.md` one row in the module table

**Interfaces:**
- `InstagramAccountService.restore_sessions(session)` loads JSON if file exists, health-check via fakeable `account_info`; failure → `is_connected=False`

- [ ] **Step 1: Failing test restore with fake client factory**

```python
@pytest.mark.asyncio
async def test_restore_dead_session_marks_disconnected(tmp_path, db_session):
    ...
```

OpenAPI test: `"/api/v1/public/instagram"` in generated spec or router prefixes test (`tests/test_router_prefixes.py`).

- [ ] **Step 2: Run fail**

- [ ] **Step 3: Implement restore, frontend, openapi regen, README**

Keep frontend visual parity with Telegram accounts list; do not redesign the admin chrome.

- [ ] **Step 4: Tests**

Run: `pytest tests/test_router_prefixes.py tests/modules/instagram_clients tests/test_frontend_openapi.py -q`

Browser: if the frontend dev server is available, log in as admin, open Instagram page, confirm list + login form render. If not, note that UI was not browser-verified.

- [ ] **Step 5: Commit**

```bash
git add src/main.py frontend docs/README.md tests
git commit -m "feat(instagram): session restore and admin UI"
```

---

## Self-review (spec coverage)

| Spec item | Task |
|-----------|------|
| Thick module A | 4–10 |
| Drop telegram_id same migration | 3–4 |
| platform + platform_user_id | 3 |
| ChatRef.channel required | 1–2 |
| Login + 2FA + challenge | 7 |
| Session JSON | 7, 10 |
| Poll inbox, no pending | 8 |
| Serial Client + thread pool | 6–8 |
| Own bus topics | 6, 9 |
| Delivery by channel | 9 |
| Voice zero on IG | 9 |
| HTTP Instagram* | 5, 7 |
| Fake Client tests | 6–10 |
| Frontend + openapi | 10 |
| No posts/voice/MQTT | out of scope, not tasked |
