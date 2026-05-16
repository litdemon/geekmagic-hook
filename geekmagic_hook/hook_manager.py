"""Claude Code hook registration and binary installation."""

import json
import logging
import os
import pathlib
import shutil
import sys
from typing import Optional

from .constants import HOOK_EVENTS, SETTINGS_HOOKS

log = logging.getLogger("geekmagic_hook")


class HookManager:
    """Manages geekmagic_hook entries in ~/.claude/settings.json.

    Also handles copying the executable to a stable, PATH-accessible
    location so hook commands keep working after the source moves.
    """

    def __init__(self, settings_path: pathlib.Path = SETTINGS_HOOKS) -> None:
        self.path = settings_path

    # ------------------------------------------------------------------
    # Hook registration
    # ------------------------------------------------------------------

    def register(self) -> None:
        """Add geekmagic_hook hook entries for all HOOK_EVENTS."""
        data = self._load_settings()
        hooks = data.setdefault("hooks", {})
        cmd_base = self.get_self_cmd()

        for event in HOOK_EVENTS:
            cmd = f"{cmd_base} --event {event}"
            entry = {"matcher": "", "hooks": [{"type": "command", "command": cmd}]}
            existing = hooks.setdefault(event, [])
            # Avoid duplicate registration on repeated setup runs
            if not any(
                h.get("hooks", [{}])[0].get("command", "") == cmd
                for h in existing
                if h.get("hooks")
            ):
                existing.append(entry)
            print(f"  ✓ {event}")

        self._save_settings(data)

    def unregister(self) -> None:
        """Remove all geekmagic_hook entries from the settings file."""
        data = self._load_settings()
        hooks = data.get("hooks", {})

        for event in HOOK_EVENTS:
            if event not in hooks:
                continue
            hooks[event] = [
                h for h in hooks[event]
                if not any(
                    self._is_our_hook(e.get("command", ""))
                    for e in h.get("hooks", [])
                )
            ]
            if not hooks[event]:
                del hooks[event]
            print(f"  ✗ {event}")

        if not hooks:
            data.pop("hooks", None)

        self._save_settings(data)

    def get_registered(self) -> list[str]:
        """Return the list of event names that have geekmagic_hook hooks registered."""
        data = self._load_settings()
        registered = []
        for event, entries in data.get("hooks", {}).items():
            if any(
                self._is_our_hook(e.get("command", ""))
                for h in entries
                for e in h.get("hooks", [])
            ):
                registered.append(event)
        return registered

    # ------------------------------------------------------------------
    # Binary installation
    # ------------------------------------------------------------------

    def install_binary(self) -> Optional[pathlib.Path]:
        """Copy this executable to the user-local bin directory.

        Called during setup so the hook command always points to a stable,
        PATH-accessible location regardless of how pip/pipx installed the package.
        Returns the installed path, or None on failure.
        """
        src = pathlib.Path(sys.argv[0]).resolve()
        dest_dir = self._user_bin_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name  # preserves .exe suffix on Windows
        try:
            if src.resolve() != dest.resolve():  # skip if already running from dest
                shutil.copy2(src, dest)
            if sys.platform != "win32":
                dest.chmod(dest.stat().st_mode | 0o111)  # ensure +x
            return dest
        except Exception as e:
            log.debug("install_binary failed: %s", e)
            return None

    def get_self_cmd(self) -> str:
        """Return the absolute path to the installed geekmagic_hook executable.

        Priority:
        1. ~/.local/bin/geekmagic_hook  (installed by setup — always stable)
        2. shutil.which()               (pipx installs a symlink here)
        3. sys.argv[0]                  (direct invocation fallback)
        """
        candidate = self._user_bin_dir() / (
            "geekmagic_hook.exe" if sys.platform == "win32" else "geekmagic_hook"
        )
        if candidate.exists():
            return str(candidate)
        found = shutil.which("geekmagic_hook")
        if found:
            return str(pathlib.Path(found).resolve())
        return str(pathlib.Path(sys.argv[0]).resolve())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _user_bin_dir(self) -> pathlib.Path:
        """Return the platform-appropriate user-local bin directory."""
        if sys.platform == "win32":
            base = pathlib.Path(os.environ.get("LOCALAPPDATA", str(pathlib.Path.home())))
            return base / "Programs" / "geekmagic_hook"
        return pathlib.Path.home() / ".local" / "bin"

    def _is_our_hook(self, command: str) -> bool:
        """Return True if *command* belongs to geekmagic_hook (any install path)."""
        exe = pathlib.Path(command.split()[0]).name
        return exe in ("geekmagic_hook", "geekmagic_hook.exe")

    def _load_settings(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return {}

    def _save_settings(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2))
