from __future__ import annotations

from dataclasses import asdict, dataclass

from .agent import analyze_session
from .forms import FormCatalog
from .llm import DraftClient
from .models import ChatMessage, Decision
from .parser import messages_until


@dataclass(frozen=True)
class FormCardView:
    title: str
    description: str
    url: str
    badge: str = "方案收集表单"
    form_id: str | None = None
    source: str = "candidate"

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayItem:
    chatseq: int
    message: ChatMessage
    decision: Decision
    candidate_card: FormCardView | None = None
    existing_card: FormCardView | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "chatseq": self.chatseq,
            "message": self.message.to_dict(),
            "decision": self.decision.to_dict(),
            "candidate_card": self.candidate_card.to_dict() if self.candidate_card else None,
            "existing_card": self.existing_card.to_dict() if self.existing_card else None,
        }


def build_replay_timeline(
    messages: list[ChatMessage],
    *,
    form_catalog: FormCatalog | None = None,
    draft_client: DraftClient | None = None,
) -> list[ReplayItem]:
    catalog = form_catalog or FormCatalog.load()
    timeline: list[ReplayItem] = []
    for message in messages:
        prefix = messages_until(messages, message.chatseq)
        decision = analyze_session(prefix, form_catalog=catalog, draft_client=draft_client)
        timeline.append(
            ReplayItem(
                chatseq=message.chatseq,
                message=message,
                decision=decision,
                candidate_card=card_from_decision(decision, catalog),
                existing_card=card_from_message(message, catalog),
            )
        )
    return timeline


def card_from_decision(decision: Decision, catalog: FormCatalog) -> FormCardView | None:
    if decision.action_type != "send_form" or not decision.form_id:
        return None
    form = catalog.by_id(decision.form_id)
    if form is None:
        return None
    return FormCardView(
        title=form.title,
        description=form.description,
        url=form.url,
        form_id=form.form_id,
        source="candidate",
    )


def card_from_message(message: ChatMessage, catalog: FormCatalog) -> FormCardView | None:
    if message.message_type != "card":
        return None
    url = _extract_url(message.content)
    if url:
        form = catalog.by_url(url)
        if form:
            return FormCardView(
                title=form.title,
                description=form.description,
                url=form.url,
                form_id=form.form_id,
                source="archive",
            )
    return _card_from_raw_content(message.content, url)


def _card_from_raw_content(content: str, url: str | None) -> FormCardView | None:
    lines = [line.strip(" *") for line in content.splitlines() if line.strip()]
    if not lines:
        return None
    first = lines[0]
    inline_title = ""
    if first.startswith("【") and "】" in first:
        marker_end = first.index("】")
        badge = first[1:marker_end]
        inline_title = first[marker_end + 1 :].strip()
    else:
        badge = "资讯卡片"
    title = inline_title or next((line for line in lines[1:] if not line.startswith("http") and "＞" not in line), first)
    description_parts = [
        line
        for line in lines[1:]
        if line != title and not line.startswith("http") and "＞" not in line and not line.startswith("立即")
    ]
    description = "\n".join(description_parts) or title
    return FormCardView(
        title=title,
        description=description,
        url=url or "",
        badge=badge,
        source="archive",
    )


def _extract_url(content: str) -> str | None:
    for token in content.replace("\n", " ").split():
        if token.startswith("http://") or token.startswith("https://"):
            return token
    return None
