# Instagram clients (instagrapi) — DM companion

Thick integration module `instagram_clients`, parallel to `telegram_clients`. Library: [instagrapi](https://github.com/subzeroid/instagrapi). v1 is **Direct inbox companion** only: login, poll DMs, same chat pipeline, send text back.

## Decisions (locked)

- Approach **A**: new module, own bus topics, own HTTP. No shared `messaging` package. No publishing onto `telegram_clients.*` topics.
- Identity: `User` is `(platform, platform_user_id)`. **`telegram_id` is dropped in the same migration** (no compat column). Backfill: `platform='telegram'`, `platform_user_id=str(<old telegram_id>)`.
- Login: username + password + 2FA/challenge HTTP. Password never persisted. Session = instagrapi `get_settings()` JSON on disk.
- Incoming: **poll Direct inbox** (not MQTT, not pending-request auto-approve).
- `ChatRef` becomes channel-aware. Delivery publishes `*.command.send_message` on the module matching `chat.channel`.
- v1: text only. No `send_voice`, no `chat_action`, no posts/stories.
- instagrapi is sync: all Client calls run in a thread pool. One operation queue per account (no parallel calls on the same `Client`).
- Copy ADR 0001 thick-module layout from `telegram_clients`.

## Out of scope (v1)

- Pending message requests / auto-accept.
- Voice, photo STT, stickers, story replies.
- Posts, reels, comments.
- Shared channel adapter / `messaging.event.*`.
- Real Instagram in CI.
- Storing passwords.
- MQTT/realtime fallback.

## Module layout

```text
src/modules/instagram_clients/
├── models.py
├── repository.py
├── config.py
├── constants.py
├── dependencies.py
├── exceptions.py
├── handlers.py
├── adapters/
│   ├── client_manager.py    # Client map, poll loops, send, session dump
│   └── login.py             # login / 2FA / challenge
├── services/
│   ├── account.py
│   ├── settings.py
│   └── chat_state.py
├── routers/
│   ├── public.py
│   ├── public_accounts.py
│   ├── public_auth.py
│   ├── public_settings.py
│   └── public_whitelist.py
└── schemas/
    ├── public.py
    └── events.py
```

- `InstagramClientManager` lives in `ApplicationContainer`.
- `configure_instagram_client_manager` / `get_instagram_client_manager()` — without configure → `RuntimeError` (same as Telethon).
- HTTP prefix: `/api/v1/public/instagram`. Barrel exports `public_router`.
- Sessions: `sessions/instagram/{account_id}.json`.

## Data

### `instagram_account`

| Column | Notes |
|--------|--------|
| `id` UUID PK | |
| `username` | login handle |
| `instagram_pk` | nullable until first successful login |
| `session_file` | path to settings JSON |
| `is_connected` | may go stale; poll loop is source of truth at runtime |
| `first_name` / `last_name` / `full_name` | from profile after login |

No password column.

### `instagram_settings`

Mirror `telegram_settings`: `account_id` FK cascade, `use_whitelist` default true, `whitelist_user_pks` JSON list (IG user pk). Empty list + whitelist on = nobody.

Admin CRUD for whitelist entries matches telegram public whitelist routes (mutate the JSON list).

### `instagram_chat_state`

`(account_id, thread_id)` unique. `last_item_id` (string or bigint — store as **string**: instagrapi item ids are not always int-safe). Used so restart does not re-emit inbox history.

### `user` (breaking)

Drop `telegram_id`. Add:

- `platform`: `str` (`telegram` | `instagram`)
- `platform_user_id`: `str` (TG numeric id as decimal string, or IG pk as decimal string)

Unique constraint `(platform, platform_user_id)`.

`get_or_create_from_telegram` → `get_or_create_from_platform(platform, platform_user_id, ...)`. HTTP `UserCreate` / `UserRead` use the new fields. Frontend users page follows OpenAPI regen.

Alembic: add columns → backfill from `telegram_id` → unique + not null → drop `telegram_id` in **one** revision.

## Adapter (instagrapi)

### Login

1. Create account row + empty session path.
2. `POST login` `{username, password}` → `Client.login` in executor.
3. `TwoFactorRequired` / `ChallengeRequired` → `ConflictError` with `login_state` (`two_factor` | `challenge`). HTTP 409.
4. `POST two-factor` / `POST challenge` with `{code}`.
5. Success: `dump_settings`, set pk/names, `is_connected=True`, publish `account.connected`, start poll task.

On app startup: for each account with a session file, `set_settings` + a cheap call (`get_timeline_feed` or `account_info`). Dead session → `is_connected=False`, no poll; admin must login again.

Disconnect: stop poll task, `is_connected=False`, `account.disconnected`.

### Poll

- One asyncio task per connected account. Interval from config (default 20s + jitter).
- `direct_threads` inbox only. **Do not** ingest pending requests.
- Skip items from `account.pk` (own outbound).
- Dedupe: persist `last_item_id` per thread; skip older/equal.
- Text → `IgMessageReceived`. Other item types: optional `media` stub list, `text=None`; orchestrator already knows how to skip empty text without STT for IG (no voice command in v1).
- Rate limit / `PleaseWait`: backoff, do not tight-loop login.
- Challenge during poll: stop loop, `is_connected=False`, `account.disconnected`.

### Send

- Serialize all Client use per account through an asyncio lock (or serial queue).
- `direct_send` to thread (resolve thread by `chat_id` = thread_id).
- Publish `message.sent` with success/error.

### Process notes

instagrapi is blocking. Never call it on the event loop. Tests inject a fake Client; manager must not import-network in unit tests.

## Bus

```
instagram_clients.event.message.received
instagram_clients.event.message.sent
instagram_clients.event.account.connected
instagram_clients.event.account.disconnected
instagram_clients.command.send_message
```

Payloads parallel TG events (`account_id`, `chat_id` = thread_id, `message_id` as str, `sender` Person with `sender_id` = IG pk).

### ChatRef

```python
channel: Literal["telegram", "instagram"]  # required
account_id: UUID | None
chat_id: int  # TG chat id or IG thread_id (thread_id must fit int; if not, use str — prefer int if instagrapi thread pk is int)
conversation_id: UUID | None
```

`state_key()` = `(channel, account_id, chat_id)`. `from_payload` **requires** `channel`. Missing channel is an error, not default telegram.

Orchestrator: subscribe to both `TG_MESSAGE_RECEIVED` and `IG_MESSAGE_RECEIVED`. On delivery, publish send command to the topic for `chat.channel`. Batching/memory/behavior/llm keep carrying ChatRef; they must not assume telegram-only field names (`telegram_chat_id` replaced).

Whitelist miss: no bus event.

## HTTP

Prefix `/api/v1/public/instagram`. Schema names prefixed `Instagram*` (`InstagramAccountCreate` / `Update` / `Read`). Password only on login body.

| Area | Behavior |
|------|----------|
| accounts | CRUD, disconnect, connection flag |
| auth | login, two-factor, challenge |
| settings | `use_whitelist` |
| whitelist | add/remove IG user pk |

Service boundary: `AppException` subclasses. No `HTTPException` in services.

Frontend: Instagram page modeled on the Telegram accounts page. After schema change: `python scripts/generate_frontend_openapi.py` and `npm run generate:api`.

## Pipeline (v1)

```
IG poll → received
  → orchestrator (no STT)
  → users get_or_create (platform=instagram)
  → batching → memory → behavior intake
       ignore → stop
       respond → LLM → behavior delivery
            text → instagram_clients.command.send_message
            voice → **force text** for channel=instagram (hard filter; no TTS)
```

Behavior voice weight is zero when `channel=instagram` so we do not call TTS for IG in v1.

## Testing

- Fake `Client`: login, 2FA, dump/load settings, threads/items, send.
- Poll dedupe + own-message filter + whitelist drop.
- ChatRef.channel routes send to IG topic not TG.
- User migration/service without `telegram_id`.
- No live Instagram in CI.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Parallel module, not shared messaging | ADR 0001; isolate IG bans from Telethon |
| Drop `telegram_id` immediately | User request; one migration, one User contract |
| Poll inbox only | instagrapi has no Telethon-grade realtime; pending inbox is ban/spam risk |
| Session JSON, no password at rest | instagrapi settings dump is the session |
| Serial Client + executor | Library is sync and rate-limit sensitive |
| Text-only delivery on IG | Voice/Direct via instagrapi is extra risk; behavior zeros voice |
| ChatRef.channel required | Prevent IG ids hitting TG send |

## Open Questions

None remaining from the design conversation.

## PR Plan

### PR1 — Domain: User + ChatRef

- Files: `users` model/schemas/service/repo/tests, alembic, `src/domain/chat.py`, all ChatRef consumers (`batching`, `orchestrator`, `behavior`, `memory`, `llm`, telegram handlers/events).
- Deps: none.
- Breaking: drop `telegram_id`; require `channel` on ChatRef. Telegram path sets `channel="telegram"`.

### PR2 — `instagram_clients` skeleton + persistence + HTTP

- Files: new module models/repos/services/routers/schemas, container, `main.py` include router, alembic tables, OpenAPI + frontend stub page.
- Deps: PR1 (users shape).
- No live Client required: manager interface + fake.

### PR3 — Login / 2FA / session + poll + bus

- Files: adapters, handlers, `bus_topics`, orchestrator subscribe/publish by channel, behavior voice filter for instagram, tests with fake Client.
- Deps: PR1, PR2.
- Wire startup restore sessions + poll tasks; shutdown cancels tasks.

Each PR is independently reviewable; companion IG path works only after PR3.
