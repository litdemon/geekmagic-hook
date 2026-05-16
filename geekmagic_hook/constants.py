"""Global constants and path definitions for geekmagic_hook."""

import pathlib

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HOME_DIR = pathlib.Path.home() / ".geekmagic_hook"
CONFIG_FILE = HOME_DIR / "config.json"
STATE_FILE = HOME_DIR / "state.json"
LOG_DIR = HOME_DIR / "logs"
LOG_FILE = LOG_DIR / "hook.log"
THEMES_DIR = HOME_DIR / "themes"

BUNDLE_THEMES_DIR = pathlib.Path(__file__).parent / "themes"

SETTINGS_LOCAL = pathlib.Path.home() / ".claude" / "settings.local.json"
SETTINGS_HOOKS = pathlib.Path.home() / ".claude" / "settings.json"

# ---------------------------------------------------------------------------
# App constants
# ---------------------------------------------------------------------------

HOOK_EVENTS = [
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "Notification",
    "SubagentStop",
]

DEFAULT_THEME = "default"
PHOTO_ALBUM_THEME = 3   # Photo Album (image/GIF display mode)
HTTP_TIMEOUT = 1.5      # seconds — hooks must not block Claude Code
