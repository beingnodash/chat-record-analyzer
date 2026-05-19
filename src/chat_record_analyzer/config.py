from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv as _python_dotenv_load
except ModuleNotFoundError:
    _python_dotenv_load = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_environment(env_path: str | Path | None = None) -> bool:
    if os.getenv("CHAT_RECORD_ANALYZER_SKIP_DOTENV") == "1":
        return False
    configured_path = os.getenv("CHAT_RECORD_ANALYZER_ENV_FILE")
    path = Path(env_path or configured_path) if env_path or configured_path else PROJECT_ROOT / ".env"
    if _python_dotenv_load is not None:
        return _python_dotenv_load(path, override=False)
    return _load_simple_env(path)


def _load_simple_env(path: Path) -> bool:
    if not path.exists():
        return False
    loaded = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")
            loaded = True
    return loaded
