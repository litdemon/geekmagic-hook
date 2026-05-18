"""Display controller — maps Claude Code states to GeekMagic GIFs."""

import json
import logging
from typing import Optional

from .config import AppConfig
from .constants import DEFAULT_THEME, PHOTO_ALBUM_THEME
from .device import GeekMagic

log = logging.getLogger("geekmagic_hook")


class DisplayController:
    """Translates Claude Code hook events/states into GeekMagic display commands.

    Owns the state→GIF mapping table, permission-check logic, and the
    three-step display sequence (disable auto-switch → set theme → set image).
    """

    # Default state derived from each hook event
    EVENT_STATES: dict[str, Optional[str]] = {
        "UserPromptSubmit":  "starting",        # branched to prompt_received after first
        "PreToolUse":        "calling_tools",
        "PostToolUse":       "working",
        "Stop":              "idle",
        "Notification":      None,              # determined by message content
        "PermissionRequest": "permission",      # Claude stopped, waiting for user selection
    }

    # Maps state name → GIF filename stored on the device
    STATE_GIF_MAP: dict[str, str] = {
        "starting":        "starting.gif",        # first UserPromptSubmit in session
        "prompt_received": "prompt_received.gif",  # subsequent UserPromptSubmits
        "calling_tools":   "calling_tools.gif",    # PreToolUse (auto-approved)
        "working":         "working.gif",           # PostToolUse
        "idle":            "waiting.gif",           # Stop — waiting for next prompt
        "permission":      "permission.gif",        # needs user approval
        "rate_limited":    "rate_limited.gif",      # API rate limit hit
    }

    def __init__(self, device: GeekMagic, config: AppConfig) -> None:
        self.device = device
        self.config = config

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def show(self, state: str) -> None:
        """Switch the GeekMagic display to the GIF for *state*.

        Sequence: disable auto-switch → set Photo Album theme → set image.
        All steps use 1.5 s timeouts and log but never raise on failure.
        """
        upload_dir = self.config.get("upload_dir", "/image/")
        gif_name = self.STATE_GIF_MAP.get(state)
        if not gif_name:
            log.debug("No GIF mapped for state=%s, skipping", state)
            return

        self.device.set_auto_switch(False)
        self.device.set_theme(PHOTO_ALBUM_THEME)
        # Device filelist uses double-slash: /image//filename.gif
        image_path = upload_dir.rstrip("/") + "//" + gif_name
        ok = self.device.set_image(image_path)
        log.info("state=%s gif=%s: %s", state, gif_name, "ok" if ok else "fail")

    def parse_notification(self, stdin_data: str) -> str:
        """Parse a Notification hook JSON payload and return a state name.

        Notification events mean Claude is alerting the user — treat them as
        permission requests by default so the display always reflects that
        user attention is needed.  Rate-limit messages are the only exception
        that map to a different state.
        """
        try:
            payload = json.loads(stdin_data)
            msg = str(payload.get("message", "")).lower()
            if any(k in msg for k in ("rate", "limit", "quota", "429")):
                return "rate_limited"
        except Exception:
            pass
        return None  # unknown notifications are ignored

