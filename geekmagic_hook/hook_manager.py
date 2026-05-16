"""Claude Code hook registration and binary installation."""

import json
import logging
import os
import pathlib
import shutil
import subprocess
import sys
import sysconfig
from typing import Optional

from .constants import HOOK_EVENTS, SETTINGS_HOOKS

log = logging.getLogger("geekmagic_hook")


class HookManager:
    """Manages geekmagic_hook entries in ~/.claude/settings.json.

    Also handles installing the package via pip so the entry-point binary
    lands in the correct user-scripts directory and hooks can reference it
    with a stable, PATH-accessible path.
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
        """Install the package via pip and return the entry-point path.

        Runs ``pip install -e <project_root>`` so the geekmagic_hook script
        is placed in the standard user-scripts directory
        (e.g. ~/.local/bin on Linux, ~/Library/Python/X.Y/bin on macOS)
        and package metadata (version etc.) stays up to date.

        Falls back to writing a minimal wrapper script if pip fails.

        Returns the installed binary path, or None on complete failure.
        """
        pkg_root = pathlib.Path(__file__).parent.parent.resolve()
        exe_name = "geekmagic_hook.exe" if sys.platform == "win32" else "geekmagic_hook"

        # --- pip install -e <project_root> ---
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(pkg_root)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # Find where pip put the script
            installed = self._find_pip_script(exe_name)
            if installed:
                return installed
            log.debug("pip succeeded but script not found on PATH; stderr=%s", result.stderr.strip())
        else:
            log.debug("pip install -e failed: %s", result.stderr.strip())

        # --- Fallback: wrapper script ---
        return self._write_wrapper(exe_name, str(pkg_root))

    def get_self_cmd(self) -> str:
        """Return the absolute path to the installed geekmagic_hook executable.

        Priority:
        1. Python user-scripts dir  (pip --user install / pip install -e .)
        2. shutil.which()            (pipx, system install, or custom PATH)
        3. sys.argv[0]               (direct invocation fallback)
        """
        exe_name = "geekmagic_hook.exe" if sys.platform == "win32" else "geekmagic_hook"

        candidate = self._user_bin_dir() / exe_name
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
        """Return the Python user-scripts directory for the running interpreter.

        Uses sysconfig so the path matches exactly where pip --user installs
        scripts (e.g. ~/Library/Python/3.9/bin on macOS, ~/.local/bin on Linux).
        """
        if sys.platform == "win32":
            base = pathlib.Path(os.environ.get("LOCALAPPDATA", str(pathlib.Path.home())))
            return base / "Programs" / "geekmagic_hook"

        scheme = "posix_user"
        scripts = sysconfig.get_path("scripts", scheme)
        if scripts:
            return pathlib.Path(scripts)
        return pathlib.Path.home() / ".local" / "bin"   # sane fallback

    def _find_pip_script(self, exe_name: str) -> Optional[pathlib.Path]:
        """Locate the script that pip just installed."""
        # 1. Known user-scripts dir
        candidate = self._user_bin_dir() / exe_name
        if candidate.exists():
            return candidate

        # 2. PATH (covers system-wide or virtualenv installs)
        found = shutil.which("geekmagic_hook")
        if found:
            return pathlib.Path(found).resolve()

        return None

    def _write_wrapper(self, exe_name: str, pkg_root: str) -> Optional[pathlib.Path]:
        """Write a minimal Python shim as a fallback when pip is unavailable."""
        dest_dir = self._user_bin_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / exe_name

        wrapper = (
            "#!/usr/bin/env python3\n"
            "# Auto-generated by geekmagic_hook setup — do not edit\n"
            "import sys, os\n"
            f"_src = {pkg_root!r}\n"
            "if os.path.isdir(_src) and _src not in sys.path:\n"
            "    sys.path.insert(0, _src)\n"
            "from geekmagic_hook.cli import main\n"
            "sys.exit(main())\n"
        )

        try:
            dest.write_text(wrapper)
            if sys.platform != "win32":
                dest.chmod(dest.stat().st_mode | 0o111)
            log.debug("Wrote wrapper to %s", dest)
            return dest
        except Exception as e:
            log.debug("_write_wrapper failed: %s", e)
            return None

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
