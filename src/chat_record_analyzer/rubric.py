from __future__ import annotations

from .models import ChatMessage, RubricScores


def clamp_score(value: int) -> int:
    return max(0, min(5, value))


def evaluate_rubric(
    messages: list[ChatMessage],
    *,
    should_send: bool,
    action_type: str,
    evidence_chatseqs: list[int],
    form_keywords_matched: int = 0,
) -> RubricScores:
    last = messages[-1] if messages else None
    evidence_strength = 1 + min(len(evidence_chatseqs), 4)

    timing = 4 if should_send else 5
    if last and last.role in {"bot", "internal_user"} and should_send:
        timing = 1

    usefulness = 4 if should_send else 3
    if action_type == "send_form":
        usefulness = 5

    non_intrusion = 5
    if should_send and last and last.role not in {"external_vendor", "external_owner"}:
        non_intrusion = 2
    elif should_send:
        non_intrusion = 4

    form_fit = 5 if action_type != "send_form" else clamp_score(2 + form_keywords_matched)

    return RubricScores(
        evidence_strength=clamp_score(evidence_strength),
        timing=clamp_score(timing),
        usefulness=clamp_score(usefulness),
        non_intrusion=clamp_score(non_intrusion),
        form_fit=clamp_score(form_fit),
    )
