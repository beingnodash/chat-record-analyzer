from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .llm import DeepSeekDraftClient, DraftClient, MockDraftClient


DraftMode = Literal["mock", "deepseek"]


@dataclass(frozen=True)
class DraftClientSelection:
    requested_mode: DraftMode
    active_mode: DraftMode
    client: DraftClient
    status_message: str
    using_fallback: bool = False


def select_draft_client(mode: DraftMode) -> DraftClientSelection:
    if mode == "mock":
        return DraftClientSelection(
            requested_mode="mock",
            active_mode="mock",
            client=MockDraftClient(),
            status_message="当前使用 Mock 话术生成，适合离线演示和稳定回归。",
        )

    deepseek = DeepSeekDraftClient.from_env()
    if deepseek is None:
        return DraftClientSelection(
            requested_mode="deepseek",
            active_mode="mock",
            client=MockDraftClient(),
            status_message="未检测到 DEEPSEEK_API_KEY，已自动回退到 Mock。",
            using_fallback=True,
        )

    return DraftClientSelection(
        requested_mode="deepseek",
        active_mode="deepseek",
        client=deepseek,
        status_message="当前使用 DeepSeek API 润色话术。",
    )
