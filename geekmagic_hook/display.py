"""Display controller — maps Claude Code states to GeekMagic GIFs."""

import json
import logging
from typing import Optional

from .config import AppConfig
from .constants import DEFAULT_THEME, PHOTO_ALBUM_THEME, SETTINGS_HOOKS, SETTINGS_LOCAL
from .device import GeekMagic

log = logging.getLogger("geekmagic_hook")


class DisplayController:
    """Translates Claude Code hook events/states into GeekMagic display commands.

    Owns the state→GIF mapping table, permission-check logic, and the
    three-step display sequence (disable auto-switch → set theme → set image).
    """

    # Default state derived from each hook event (may be overridden in cmd_event)
    EVENT_STATES: dict[str, Optional[str]] = {
        "UserPromptSubmit": "starting",       # branched to prompt_received after first
        "PreToolUse":       "calling_tools",  # may become "permission" after stdin parse
        "PostToolUse":      "working",
        "SubagentStop":     "working",
        "Stop":             "idle",
        "Notification":     None,             # determined by message content
    }

    # Maps state name → GIF filename stored on the device
    STATE_GIF_MAP: dict[str, str] = {
        "starting":        "starting.gif",        # first UserPromptSubmit in session
        "prompt_received": "prompt_received.gif",  # subsequent UserPromptSubmits
        "calling_tools":   "calling_tools.gif",    # PreToolUse (auto-approved)
        "working":         "working.gif",           # PostToolUse / SubagentStop
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
        """Parse a Notification hook JSON payload and return a state name."""
        try:
            payload = json.loads(stdin_data)
            msg = str(payload.get("message", "")).lower()
            if any(k in msg for k in ("rate", "limit", "quota", "429")):
                return "rate_limited"
            if any(k in msg for k in ("permission", "allow", "approve", "deny")):
                return "permission"
        except Exception:
            pass
        return "working"

    def resolve_pretooluse_state(self, stdin_data: str) -> str:
        """Determine the display state for a PreToolUse event.

        Reads tool_name from stdin JSON and checks permissions.allow.
        Falls back to 'calling_tools' on any parse failure.
        """
        try:
            tool_name = json.loads(stdin_data).get("tool_name", "")
        except Exception:
            tool_name = ""

        log.debug("PreToolUse tool_name=%s", tool_name)

        if not tool_name:
            # stdin parse failure — safe fallback, don't assume permission needed
            return "calling_tools"
        if self._is_tool_pre_approved(tool_name):
            return "calling_tools"
        # tool not in permissions.allow → user will be asked for permission
        return "permission"

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _is_tool_pre_approved(self, tool_name: str) -> bool:
        """Return True if *tool_name* matches any entry in permissions.allow.

        Claude Code allow patterns look like:
          "Bash(git *)", "Read(*)", "Edit(*)", "Bash"
        We match on the tool-name prefix only (before the first '(').
        """
        for settings_path in (SETTINGS_LOCAL, SETTINGS_HOOKS):
            if not settings_path.exists():
                continue
            try:
                data = json.loads(settings_path.read_text())
                allowed = data.get("permissions", {}).get("allow", [])
                for pattern in allowed:
                    pat_tool = pattern.split("(")[0].strip()
                    if pat_tool.lower() == tool_name.lower():
                        return True
            except Exception:
                pass
        return False
