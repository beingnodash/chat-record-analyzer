from __future__ import annotations

import argparse
import json

from .agent import analyze_session
from .forms import FormCatalog
from .parser import load_messages, messages_until


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a WeCom-style chat archive JSONL file.")
    parser.add_argument("path", help="Path to canonical JSONL chat archive")
    parser.add_argument("--chatseq", type=int, default=None, help="Analyze messages up to this chatseq")
    args = parser.parse_args()

    messages = messages_until(load_messages(args.path), args.chatseq)
    decision = analyze_session(messages, form_catalog=FormCatalog.load())
    print(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
