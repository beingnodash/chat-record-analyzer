from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class DraftClient(Protocol):
    def polish(self, prompt: str, fallback: str) -> str:
        ...


@dataclass(frozen=True)
class MockDraftClient:
    def polish(self, prompt: str, fallback: str) -> str:
        return fallback


@dataclass(frozen=True)
class DeepSeekDraftClient:
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/chat/completions"
    timeout_seconds: int = 20

    @classmethod
    def from_env(cls) -> "DeepSeekDraftClient | None":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return None
        return cls(
            api_key=api_key,
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions"),
        )

    def polish(self, prompt: str, fallback: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是企业微信外部群里的业务助手机器人，只输出一段简洁、稳妥、中文的话术。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
            return fallback
        return data.get("choices", [{}])[0].get("message", {}).get("content", fallback).strip() or fallback
