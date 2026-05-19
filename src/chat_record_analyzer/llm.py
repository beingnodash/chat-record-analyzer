from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from .config import load_environment


class DraftClient(Protocol):
    def polish(self, prompt: str, fallback: str) -> str:
        ...


@dataclass(frozen=True)
class MockDraftClient:
    def polish(self, prompt: str, fallback: str) -> str:
        return fallback

    def complete_text(self, prompt: str, fallback: str) -> str:
        return fallback

    def complete_json(self, prompt: str, fallback: dict) -> dict:
        return fallback


@dataclass(frozen=True)
class DeepSeekDraftClient:
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/chat/completions"
    timeout_seconds: int = 20

    @classmethod
    def from_env(cls) -> "DeepSeekDraftClient | None":
        load_environment()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return None
        return cls(
            api_key=api_key,
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions"),
        )

    def polish(self, prompt: str, fallback: str) -> str:
        return self.complete_text(prompt, fallback)

    def complete_text(self, prompt: str, fallback: str) -> str:
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
        data = self._post(payload)
        if data is None:
            return fallback
        return data.get("choices", [{}])[0].get("message", {}).get("content", fallback).strip() or fallback

    def complete_json(self, prompt: str, fallback: dict) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是企业微信外部群业务分析助手，只返回合法 JSON，不要输出 Markdown。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        data = self._post(payload)
        if data is None:
            return fallback
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return fallback
        return parsed if isinstance(parsed, dict) else fallback

    def _post(self, payload: dict) -> dict | None:
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
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
            return None
