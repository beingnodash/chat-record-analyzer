from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Role = Literal["bot", "internal_user", "external_owner", "external_vendor", "external_other"]
MessageType = Literal["text", "card", "image", "file", "system"]
ActionType = Literal["none", "ask_for_info", "send_form"]


@dataclass(frozen=True)
class ChatMessage:
    session_id: str
    chatseq: int
    timestamp: str
    user_id: str
    display_name: str
    role: Role
    org: str
    message_type: MessageType
    content: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ChatMessage":
        required = [
            "session_id",
            "chatseq",
            "timestamp",
            "user_id",
            "display_name",
            "role",
            "org",
            "message_type",
            "content",
        ]
        missing = [key for key in required if key not in raw]
        if missing:
            raise ValueError(f"message missing required fields: {', '.join(missing)}")
        return cls(
            session_id=str(raw["session_id"]),
            chatseq=int(raw["chatseq"]),
            timestamp=str(raw["timestamp"]),
            user_id=str(raw["user_id"]),
            display_name=str(raw["display_name"]),
            role=raw["role"],
            org=str(raw["org"]),
            message_type=raw["message_type"],
            content=str(raw["content"]).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FormDefinition:
    form_id: str
    title: str
    url: str
    description: str
    keywords: list[str]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "FormDefinition":
        return cls(
            form_id=str(raw["form_id"]),
            title=str(raw["title"]),
            url=str(raw["url"]),
            description=str(raw["description"]),
            keywords=[str(keyword) for keyword in raw.get("keywords", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RubricScores:
    evidence_strength: int
    timing: int
    usefulness: int
    non_intrusion: int
    form_fit: int

    @property
    def overall(self) -> float:
        values = [
            self.evidence_strength,
            self.timing,
            self.usefulness,
            self.non_intrusion,
            self.form_fit,
        ]
        return round(sum(values) / len(values), 2)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["overall"] = self.overall
        return data


@dataclass(frozen=True)
class Decision:
    should_send: bool
    action_type: ActionType
    confidence: float
    rubric_scores: RubricScores
    rationale: str
    evidence_chatseqs: list[int] = field(default_factory=list)
    draft_message: str = ""
    form_id: str | None = None
    form_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rubric_scores"] = self.rubric_scores.to_dict()
        return data
