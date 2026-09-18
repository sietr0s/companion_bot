"""
Конфигурация топиков шины сообщений.

Соглашение об именовании:
  - {module}.event.{domain_action}  — событие владельца модуля
  - {module}.command.{action}       — команда другому модулю
"""


class BusTopics:
    """Реестр топиков шины сообщений."""

    USER_REGISTERED: str = "auth.event.user.registered"
    USER_LOGGED_IN: str = "auth.event.user.logged_in"
    USER_DELETED: str = "auth.event.user.deleted"

    USER_CREATED: str = "users.event.created"
    USER_UPDATED: str = "users.event.updated"

    TG_MESSAGE_RECEIVED: str = "telegram_clients.event.message.received"
    TG_MESSAGE_SENT: str = "telegram_clients.event.message.sent"
    TG_ACCOUNT_CONNECTED: str = "telegram_clients.event.account.connected"
    TG_ACCOUNT_DISCONNECTED: str = "telegram_clients.event.account.disconnected"
    TG_MESSAGE_SEND: str = "telegram_clients.command.send_message"
    TG_MESSAGE_SEND_VOICE: str = "telegram_clients.command.send_voice"
    TG_CHAT_ACTION: str = "telegram_clients.command.chat_action"

    IG_MESSAGE_RECEIVED: str = "instagram_clients.event.message.received"
    IG_MESSAGE_SENT: str = "instagram_clients.event.message.sent"
    IG_ACCOUNT_CONNECTED: str = "instagram_clients.event.account.connected"
    IG_ACCOUNT_DISCONNECTED: str = "instagram_clients.event.account.disconnected"
    IG_MESSAGE_SEND: str = "instagram_clients.command.send_message"

    BATCH_ADD_MESSAGE: str = "batching.command.add_message"
    BATCH_READY: str = "batching.event.batch.ready"
    BATCH_COMPLETED: str = "batching.event.batch.completed"

    MEMORY_PROCESS_BATCH: str = "memory.command.process_batch"
    MEMORY_BUILD_CONTEXT: str = "memory.command.build_context"
    MEMORY_UPDATE: str = "memory.command.update_memory"
    MEMORY_MAINTAIN: str = "memory.command.maintain"
    MEMORY_BATCH_PROCESSED: str = "memory.event.batch.processed"
    MEMORY_CONTEXT_BUILT: str = "memory.event.context.built"
    MEMORY_UPDATED: str = "memory.event.memory.updated"

    LLM_GENERATE_REPLY: str = "llm.command.generate_reply"
    LLM_SUMMARIZE: str = "llm.command.summarize"
    LLM_REPLY_GENERATED: str = "llm.event.reply.generated"
    LLM_REPLY_SUPPRESSED: str = "llm.event.reply.suppressed"
    LLM_SUMMARY_GENERATED: str = "llm.event.summary.generated"

    STT_TRANSCRIBE: str = "stt.command.transcribe"
    STT_TRANSCRIBED: str = "stt.event.transcribed"
    STT_TRANSCRIBE_FAILED: str = "stt.event.transcribe_failed"

    TTS_SYNTHESIZE: str = "tts.command.synthesize"
    TTS_SYNTHESIZED: str = "tts.event.synthesized"
    TTS_SYNTHESIZE_SKIPPED: str = "tts.event.synthesize_skipped"

    BEHAVIOR_DECIDE_INTAKE: str = "behavior.command.decide_intake"
    BEHAVIOR_INTAKE_DECIDED: str = "behavior.event.intake_decided"
    BEHAVIOR_DECIDE_DELIVERY: str = "behavior.command.decide_delivery"
    BEHAVIOR_DELIVERY_DECIDED: str = "behavior.event.delivery_decided"
    BEHAVIOR_NOTE_DELIVERY: str = "behavior.command.note_delivery"
