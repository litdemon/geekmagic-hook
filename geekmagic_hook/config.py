"""Configuration and hook-state persistence for geekmagic_hook."""

import json
import logging
import time
from typing import Optional

from .constants import CONFIG_FILE, DEFAULT_THEME, HOME_DIR, STATE_FILE

log = logging.getLogger("geekmagic_hook")


class AppConfig:
    """Persistent application configuration backed by ~/.geekmagic_hook/config.json."""

    DEFAULTS: dict = {
        "device_ip": None,
        "active_theme": DEFAULT_THEME,
        "upload_dir": "/image/",
        "log_level": "INFO",
    }

    def __init__(self) -> None:
        self._data = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                return {**self.DEFAULTS, **json.loads(CONFIG_FILE.read_text())}
            except Exception:
                pass
        return dict(self.DEFAULTS)

    def save(self) -> None:
        HOME_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(self._data, indent=2))

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value

    def to_dict(self) -> dict:
        return dict(self._data)


class HookState:
    """Tracks the current Claude Code display state to prevent redundant API calls.

    Persisted in ~/.geekmagic_hook/state.json as {"current": <state_name>, ...}.
    """

    def __init__(self) -> None:
        self._data = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except Exception:
                pass
        return {"current": None}

    def save(self) -> None:
        HOME_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self._data))

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def current(self) -> Optional[str]:
        return self._data.get("current")

    def update(self, state: str, event: str) -> None:
        """Persist a new state and timestamp."""
        self._data = {"current": state, "event": event, "ts": time.time()}
        self.save()

    def to_dict(self) -> dict:
        return dict(self._data)
