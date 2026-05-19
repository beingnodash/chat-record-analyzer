from __future__ import annotations

import json
from pathlib import Path

from .models import FormDefinition


DEFAULT_FORMS_PATH = Path(__file__).resolve().parents[2] / "data" / "forms.json"


class FormCatalog:
    def __init__(self, forms: list[FormDefinition]):
        if not forms:
            raise ValueError("form catalog must contain at least one form")
        self.forms = forms

    @classmethod
    def load(cls, path: str | Path = DEFAULT_FORMS_PATH) -> "FormCatalog":
        raw_forms = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls([FormDefinition.from_dict(raw) for raw in raw_forms])

    def best_match(self, text: str) -> FormDefinition:
        normalized = text.lower()
        scored: list[tuple[int, FormDefinition]] = []
        for form in self.forms:
            score = sum(1 for keyword in form.keywords if keyword.lower() in normalized)
            scored.append((score, form))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]
