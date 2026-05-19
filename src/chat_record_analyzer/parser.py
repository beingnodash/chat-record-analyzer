from __future__ import annotations

import json
from pathlib import Path

from .models import ChatMessage


def parse_jsonl(text: str) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_number}: {exc.msg}") from exc
        messages.append(ChatMessage.from_dict(raw))
    return sorted(messages, key=lambda message: message.chatseq)


def load_messages(path: str | Path) -> list[ChatMessage]:
    return parse_jsonl(Path(path).read_text(encoding="utf-8"))


def messages_until(messages: list[ChatMessage], chatseq: int | None) -> list[ChatMessage]:
    if chatseq is None:
        return list(messages)
    return [message for message in messages if message.chatseq <= chatseq]
