from __future__ import annotations

import argparse
import json

from .agent import analyze_session
from .config import load_environment
from .forms import FormCatalog
from .runtime import select_draft_client
from .parser import load_messages, messages_until


def main() -> None:
    load_environment()
    parser = argparse.ArgumentParser(description="Analyze a WeCom-style chat archive JSONL file.")
    parser.add_argument("path", help="Path to canonical JSONL chat archive")
    parser.add_argument("--chatseq", type=int, default=None, help="Analyze messages up to this chatseq")
    parser.add_argument("--draft-mode", choices=["mock", "deepseek"], default="mock", help="Draft generation mode")
    args = parser.parse_args()

    messages = messages_until(load_messages(args.path), args.chatseq)
    selection = select_draft_client(args.draft_mode)
    decision = analyze_session(messages, form_catalog=FormCatalog.load(), draft_client=selection.client)
    print(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
