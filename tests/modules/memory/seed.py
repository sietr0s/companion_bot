from src.modules.memory.repository import MessageBatchRepository, MessageRepository


async def insert_message(
    session,
    conversation_id,
    *,
    text: str,
    sequence_number: int,
    direction: str = "incoming",
    message_type: str = "text",
    batch_id=None,
):
    if batch_id is None:
        batch = await MessageBatchRepository().create(
            session,
            {"conversation_id": conversation_id, "direction": direction},
        )
        batch_id = batch.id
    return await MessageRepository().create(
        session,
        {
            "conversation_id": conversation_id,
            "batch_id": batch_id,
            "text": text,
            "direction": direction,
            "message_type": message_type,
            "sequence_number": sequence_number,
        },
    )


def vector_payload(
    conversation_id, text, *, kind="topic", embedding, seq_from=1, seq_to=1, **extra
):
    data = {
        "conversation_id": conversation_id,
        "text": text,
        "kind": kind,
        "embedding": embedding,
        "seq_from": seq_from,
        "seq_to": seq_to,
        "partial": extra.get("partial", False),
    }
    return data
