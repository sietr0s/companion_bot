"""Pure formatting of policy diagnostics."""


def _weights(values: dict[str, float]) -> str:
    return ", ".join(f"{name}={value:.3f}" for name, value in values.items())


def format_pre_softmax_log(
    *,
    policy: str,
    base: dict[str, float],
    contributions: list[tuple[str, dict[str, float]]],
    after_criteria: dict[str, float],
    blocked: dict[str, str],
    before_softmax: dict[str, float],
) -> str:
    lines = [f"Policy: {policy}", f"Base: {_weights(base)}"]
    lines.extend(f"{name}: {_weights(deltas)}" for name, deltas in contributions)
    lines.extend(
        [
            f"After criteria: {_weights(after_criteria)}",
            f"Blocked: {blocked}",
            f"Before sampling: {_weights(before_softmax)}",
        ]
    )
    return "\n".join(lines)


def format_decision_log(
    *,
    stage: str,
    action: str,
    text: str,
    probabilities: dict[str, float],
    scores: dict[str, float],
    chat_id: int,
    activity: str | None = None,
    mood: str | None = None,
    blocked: list[str] | None = None,
    incoming_types: list[str] | None = None,
) -> str:
    return "\n".join(
        [
            f"Decision: {stage} chat={chat_id} action={action}",
            f"Life: activity={activity} mood={mood}",
            f"Scores: {_weights(scores)}",
            f"Probabilities: {_weights(probabilities)}",
            f"Blocked: {blocked or []}; incoming: {incoming_types or []}",
            f"Text: {text}",
        ]
    )
