#!/usr/bin/env python3
"""
geekmagic_hook - Claude Code hook executor for GeekMagic SmallTV-Ultra display
Usage:
  geekmagic_hook setup              # discover device + register hooks
  geekmagic_hook uninstall          # remove all hooks
  geekmagic_hook status             # show device + hook status
  geekmagic_hook test               # cycle through all states visually
  geekmagic_hook discover           # re-scan network for device
  geekmagic_hook logs               # tail hook log
  geekmagic_hook theme list         # list uploaded themes
  geekmagic_hook theme upload <dir> # upload theme GIFs to device
  geekmagic_hook --event <name>     # hook execution mode (called by Claude Code)
"""

import argparse
import json
import logging
import logging.handlers
import os
import pathlib
import shutil
import socket
import sys
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

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

SETTINGS_LOCAL = pathlib.Path.home() / ".claude" / "settings.local.json"  # permissions only
SETTINGS_HOOKS = pathlib.Path.home() / ".claude" / "settings.json"  # hooks must be here

HOOK_EVENTS = [
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "Notification",
    "SubagentStop",
]

DEFAULT_THEME = "default"
PHOTO_ALBUM_THEME = 3  # Photo Album (image/GIF display mode)

HTTP_TIMEOUT = 1.5  # seconds — hooks must not block Claude Code

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(verbose: bool = False) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("geekmagic_hook")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1024 * 1024, backupCount=3
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)

    if verbose:
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(sh)

    return logger


log = logging.getLogger("geekmagic_hook")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "device_ip": None,
    "active_theme": DEFAULT_THEME,
    "upload_dir": "/image/",
    "log_level": "INFO",
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return {**DEFAULT_CONFIG, **json.loads(CONFIG_FILE.read_text())}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"current": None}


def save_state(state: dict) -> None:
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state))


# ---------------------------------------------------------------------------
# GeekMagic HTTP API
# ---------------------------------------------------------------------------

class GeekMagic:
    def __init__(self, ip: str):
        self.base = f"http://{ip}"

    def _get(self, path: str) -> Optional[str]:
        try:
            url = self.base + path
            with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as r:
                return r.read().decode()
        except Exception as e:
            log.debug("GET %s failed: %s", path, e)
            return None

    def _upload(self, path: str, filename: str, data: bytes) -> bool:
        boundary = "GeekMagicBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: image/gif\r\n\r\n"
        ).encode() + data + f"\r\n--{boundary}--\r\n".encode()

        try:
            req = urllib.request.Request(
                self.base + path,
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            # Device responds with updated filelist HTML (not "OK") on success
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = r.read().decode()
                return r.status == 200 or filename in resp
        except Exception as e:
            log.debug("Upload %s failed: %s", filename, e)
            return False

    def is_online(self) -> bool:
        return self._get("/v.json") is not None

    def get_info(self) -> Optional[dict]:
        raw = self._get("/v.json")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    def get_space(self) -> Optional[dict]:
        raw = self._get("/space.json")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    def set_theme(self, theme_id: int) -> bool:
        return self._get(f"/set?theme={theme_id}") == "OK"

    def get_theme_list(self) -> Optional[dict]:
        """Return current auto-switch settings: {list, sw_en, sw_i}."""
        raw = self._get("/theme_list.json")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    def set_auto_switch(self, enabled: bool) -> bool:
        """Toggle auto theme switching, preserving the user's theme list and interval.

        Skips the API call if sw_en is already in the desired state to avoid a
        firmware side-effect: sending theme_list back to the device causes it to
        momentarily activate the first entry in the list (e.g. Weather Clock Today)
        before our subsequent set_theme(PHOTO_ALBUM_THEME) call overrides it.
        """
        tl = self.get_theme_list()
        if not tl:
            return False
        desired = "1" if enabled else "0"
        if tl.get("sw_en", "0") == desired:
            log.debug("set_auto_switch: already sw_en=%s, skipping", desired)
            return True  # already in desired state — no API call needed
        theme_list = tl.get("list", "0,0,1,1,0,0,0")
        sw_i = tl.get("sw_i", "30")
        return self._get(
            f"/set?theme_list={theme_list}&sw_en={desired}&theme_interval={sw_i}"
        ) == "OK"

    def set_image(self, image_path: str) -> bool:
        # Device expects raw (un-encoded) path; double-slash format per filelist
        return self._get(f"/set?img={image_path}") == "OK"

    def upload_gif(self, upload_dir: str, local_path: pathlib.Path) -> bool:
        data = local_path.read_bytes()
        encoded_dir = urllib.parse.quote(upload_dir)
        return self._upload(f"/doUpload?dir={encoded_dir}", local_path.name, data)

    def list_files(self, directory: str) -> Optional[str]:
        encoded = urllib.parse.quote(directory)
        return self._get(f"/filelist?dir={encoded}")

    def get_active_theme(self) -> Optional[int]:
        raw = self._get("/app.json")
        if raw:
            try:
                return json.loads(raw).get("theme")
            except Exception:
                pass
        return None


# ---------------------------------------------------------------------------
# Network discovery
# ---------------------------------------------------------------------------

def _check_ip(ip: str, results: list, lock: threading.Lock) -> None:
    try:
        url = f"http://{ip}/v.json"
        with urllib.request.urlopen(url, timeout=0.8) as r:
            data = json.loads(r.read().decode())
            if "m" in data and "v" in data:
                with lock:
                    results.append((ip, data))
    except Exception:
        pass


def discover_devices(subnet: Optional[str] = None) -> list[tuple[str, dict]]:
    """Scan local subnet for GeekMagic devices. Returns list of (ip, info)."""
    if subnet is None:
        # Guess local subnet from default gateway interface
        subnet = _guess_subnet()

    print(f"  Scanning {subnet}.1-254 …", flush=True)
    results: list = []
    lock = threading.Lock()
    threads = []

    for i in range(1, 255):
        ip = f"{subnet}.{i}"
        t = threading.Thread(target=_check_ip, args=(ip, results, lock), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=2.0)

    return results


def _prompt(msg: str, default: str = "") -> str:
    """input() wrapper that handles EOF gracefully (non-interactive environments)."""
    try:
        return input(msg).strip()
    except EOFError:
        return default


def _guess_subnet() -> str:
    """Return subnet prefix like '192.168.1' by creating a UDP socket."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ".".join(ip.split(".")[:3])
    except Exception:
        return "192.168.1"


# ---------------------------------------------------------------------------
# Hook state → display
# ---------------------------------------------------------------------------

EVENT_STATES = {
    "UserPromptSubmit": "starting",   # cmd_event branches to prompt_received after first
    "PreToolUse":       "calling_tools",
    "PostToolUse":      "working",
    "SubagentStop":     "working",
    "Stop":             "idle",
    "Notification":     None,         # determined by message content
}


def _gif_name_for(state: str, theme: str) -> Optional[str]:
    """Return GIF filename for given state and theme."""
    mapping = {
        "starting":        "starting.gif",       # first UserPromptSubmit in session
        "prompt_received": "prompt_received.gif", # subsequent UserPromptSubmits
        "calling_tools":   "calling_tools.gif",   # PreToolUse
        "working":         "working.gif",          # PostToolUse / SubagentStop
        "idle":            "waiting.gif",          # Stop — waiting for next prompt
        "permission":      "permission.gif",       # Notification: needs user approval
        "rate_limited":    "rate_limited.gif",     # Notification: API rate limit
    }
    return mapping.get(state)


def _parse_notification(stdin_data: str) -> str:
    """Parse Notification hook JSON and return state name."""
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


def _display_state(gm: GeekMagic, state: str, cfg: dict) -> None:
    """Update GeekMagic display for the given state.

    All states (including idle) show a GIF in Photo Album (image-only) mode.
    Auto theme switching is disabled whenever Claude Code is running so the
    display stays locked on the current GIF.
    """
    theme_name = cfg.get("active_theme", DEFAULT_THEME)
    upload_dir = cfg.get("upload_dir", "/image/")

    gif_name = _gif_name_for(state, theme_name)
    if not gif_name:
        log.debug("No GIF mapped for state=%s, skipping", state)
        return

    # Disable auto-switching so the display stays on the GIF we set
    gm.set_auto_switch(False)
    gm.set_theme(PHOTO_ALBUM_THEME)  # Photo Album = theme 3
    # Device filelist shows paths as /image//filename.gif (double slash)
    image_path = upload_dir.rstrip("/") + "//" + gif_name
    ok = gm.set_image(image_path)
    log.info("state=%s gif=%s: %s", state, gif_name, "ok" if ok else "fail")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_event(event: str) -> int:
    """Hook execution mode — called by Claude Code for each hook event."""
    setup_logging()

    cfg = load_config()
    ip = cfg.get("device_ip")
    if not ip:
        log.debug("No device configured, skipping hook %s", event)
        return 0

    gm = GeekMagic(ip)
    if not gm.is_online():
        log.info("Device %s offline, skipping hook %s", ip, event)
        return 0

    # Determine target state
    if event == "Notification":
        stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
        state = _parse_notification(stdin_data)
    elif event == "UserPromptSubmit":
        # First prompt in a fresh session → starting.gif; subsequent → prompt_received.gif
        prev = load_state().get("current")
        state = "starting" if prev is None else "prompt_received"
    else:
        state = EVENT_STATES.get(event, "working")

    # Skip redundant API calls
    current_state = load_state()
    if current_state.get("current") == state:
        log.debug("State unchanged (%s), skipping API call", state)
        return 0

    _display_state(gm, state, cfg)
    save_state({"current": state, "event": event, "ts": time.time()})
    return 0


def cmd_setup(rescan: bool = False) -> int:
    """Discover device, upload GIFs, register hooks."""
    setup_logging(verbose=True)
    HOME_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    ip = cfg.get("device_ip")

    # --- Device discovery ---
    print("\n[1/4] Searching for GeekMagic device…")
    if ip and not rescan:
        gm = GeekMagic(ip)
        if gm.is_online():
            print(f"  Using saved device at {ip}")
        else:
            print(f"  Saved device {ip} not responding, scanning…")
            ip = None

    if not ip:
        found = discover_devices()
        if found:
            ip, info = found[0]
            print(f"  Found: {ip}  model={info.get('m')}  version={info.get('v')}")
            if len(found) > 1:
                print("  (multiple devices found, using first)")
        else:
            ip = _prompt("  No device found. Enter IP manually: ")
            if not ip:
                print("Aborted.")
                return 1
            gm = GeekMagic(ip)
            if not gm.is_online():
                print(f"  Cannot reach {ip}. Aborted.")
                return 1

    gm = GeekMagic(ip)
    info = gm.get_info() or {}
    space = gm.get_space() or {}
    free_kb = space.get("free", 0) // 1024

    print(f"\n  Device: {ip}  {info.get('m','')} {info.get('v','')}")
    print(f"  Free space: {free_kb} KB")

    # --- Permission ---
    print("\n[2/4] Claude Code hook registration")
    if not SETTINGS_LOCAL.parent.exists():
        print(f"  Warning: {SETTINGS_LOCAL.parent} not found (is Claude Code installed?)")

    answer = _prompt(f"  Register hooks in {SETTINGS_HOOKS}? [y/N] ").lower()
    if answer != "y":
        print("Aborted.")
        return 0

    # --- GIF upload ---
    print("\n[3/4] Uploading GIFs to device…")
    src_dir = BUNDLE_THEMES_DIR / DEFAULT_THEME
    dest_themes = THEMES_DIR / DEFAULT_THEME
    dest_themes.mkdir(parents=True, exist_ok=True)

    upload_dir = cfg.get("upload_dir", "/image/")
    for gif in src_dir.glob("*.gif"):
        dest = dest_themes / gif.name
        if not dest.exists():
            shutil.copy2(gif, dest)
        ok = gm.upload_gif(upload_dir, gif)
        status = "ok" if ok else "FAILED"
        print(f"  {gif.name}: {status}")

    # --- Hook registration ---
    print(f"\n[4/4] Registering hooks in {SETTINGS_HOOKS}…")
    _register_hooks(SETTINGS_HOOKS)

    # --- Save config ---
    cfg["device_ip"] = ip
    save_config(cfg)

    print("\n✓ Setup complete. Restart Claude Code for hooks to take effect.")
    return 0


def cmd_uninstall() -> int:
    """Remove all hooks from settings.local.json."""
    setup_logging(verbose=True)
    print(f"Removing hooks from {SETTINGS_HOOKS}…")
    _unregister_hooks(SETTINGS_HOOKS)
    print("✓ Hooks removed. Restart Claude Code for changes to take effect.")
    return 0


def cmd_status() -> int:
    """Show device status and hook registration."""
    setup_logging(verbose=True)
    cfg = load_config()
    ip = cfg.get("device_ip")

    print("=== geekmagic_hook status ===")
    print(f"Config:        {CONFIG_FILE}")
    print(f"Home dir:      {HOME_DIR}")
    print(f"Active theme:  {cfg.get('active_theme', DEFAULT_THEME)}")
    print(f"Settings file: {SETTINGS_HOOKS} (hooks)")
    print()

    if ip:
        gm = GeekMagic(ip)
        online = gm.is_online()
        print(f"Device IP:     {ip}  {'[ONLINE]' if online else '[OFFLINE]'}")
        if online:
            info = gm.get_info() or {}
            space = gm.get_space() or {}
            free_kb = space.get("free", 0) // 1024
            total_kb = space.get("total", 0) // 1024
            active = gm.get_active_theme()
            print(f"  Model:       {info.get('m','')} {info.get('v','')}")
            print(f"  Free space:  {free_kb}/{total_kb} KB")
            print(f"  GM Theme:    {active}")
    else:
        print("Device IP:     (not configured — run 'setup')")

    print()
    # Hook registration status
    registered = _get_registered_hooks(SETTINGS_HOOKS)
    if registered:
        print(f"Registered hooks ({len(registered)}):")
        for ev in registered:
            print(f"  ✓ {ev}")
    else:
        print("No hooks registered (run 'setup' to register)")

    # Current display state
    state = load_state()
    if state.get("current"):
        ts = state.get("ts", 0)
        age = int(time.time() - ts)
        print(f"\nLast state: {state['current']}  ({age}s ago via {state.get('event','')})")

    return 0


def cmd_discover() -> int:
    """Re-scan network and update device IP."""
    setup_logging(verbose=True)
    print("Scanning network…")
    found = discover_devices()
    if not found:
        print("No GeekMagic devices found.")
        return 1

    for ip, info in found:
        print(f"  {ip}  {info.get('m','')}  {info.get('v','')}")

    if len(found) == 1:
        ip, _ = found[0]
        answer = _prompt(f"Update config to use {ip}? [y/N] ").lower()
        if answer == "y":
            cfg = load_config()
            cfg["device_ip"] = ip
            save_config(cfg)
            print(f"✓ Config updated: device_ip = {ip}")
    else:
        ips = [ip for ip, _ in found]
        choice = _prompt(f"Choose device [{', '.join(ips)}]: ")
        if choice in ips:
            cfg = load_config()
            cfg["device_ip"] = choice
            save_config(cfg)
            print(f"✓ Config updated: device_ip = {choice}")

    return 0


def cmd_test() -> int:
    """Cycle through all display states for visual verification."""
    setup_logging(verbose=True)
    cfg = load_config()
    ip = cfg.get("device_ip")
    if not ip:
        print("No device configured. Run 'setup' first.")
        return 1

    gm = GeekMagic(ip)
    if not gm.is_online():
        print(f"Device {ip} is offline.")
        return 1

    states = [
        ("starting",        "UserPromptSubmit (첫 번째)"),
        ("prompt_received", "UserPromptSubmit (이후)"),
        ("calling_tools",   "PreToolUse"),
        ("working",         "PostToolUse / SubagentStop"),
        ("permission",      "Notification (permission)"),
        ("rate_limited",    "Notification (rate_limit)"),
        ("idle",            "Stop → waiting.gif"),
    ]

    print(f"Testing display states on {ip}…")
    for state, label in states:
        print(f"  [{label}] → {state}", end=" ", flush=True)
        _display_state(gm, state, cfg)
        print("✓")
        time.sleep(2)

    print("✓ Test complete.")
    return 0


def cmd_logs(lines: int = 50) -> int:
    """Print the last N lines of the hook log."""
    if not LOG_FILE.exists():
        print(f"No log file at {LOG_FILE}")
        return 0
    text = LOG_FILE.read_text().splitlines()
    for line in text[-lines:]:
        print(line)
    return 0


def cmd_theme(action: str, args: list[str]) -> int:
    """Theme management: list or upload."""
    setup_logging(verbose=True)
    cfg = load_config()

    if action == "list":
        ip = cfg.get("device_ip")
        if ip:
            gm = GeekMagic(ip)
            if gm.is_online():
                upload_dir = cfg.get("upload_dir", "/image/")
                html = gm.list_files(upload_dir)
                if html:
                    import re
                    names = re.findall(r"href='[^']*?/([^/']+\.gif)'", html)
                    print(f"Files on device ({upload_dir}):")
                    for n in names:
                        print(f"  {n}")
                    return 0

        print("Local themes:")
        for theme_dir in THEMES_DIR.iterdir():
            if theme_dir.is_dir():
                gifs = list(theme_dir.glob("*.gif"))
                print(f"  {theme_dir.name}/  ({len(gifs)} GIFs)")
                for g in gifs:
                    print(f"    {g.name}")

    elif action == "upload":
        if not args:
            print("Usage: theme upload <directory>")
            return 1
        src = pathlib.Path(args[0]).expanduser()
        if not src.is_dir():
            print(f"Not a directory: {src}")
            return 1
        ip = cfg.get("device_ip")
        if not ip:
            print("No device configured. Run 'setup' first.")
            return 1
        gm = GeekMagic(ip)
        if not gm.is_online():
            print(f"Device {ip} is offline.")
            return 1
        upload_dir = cfg.get("upload_dir", "/image/")
        gifs = list(src.glob("*.gif"))
        print(f"Uploading {len(gifs)} GIFs from {src} to {ip}{upload_dir}…")
        for gif in gifs:
            ok = gm.upload_gif(upload_dir, gif)
            print(f"  {gif.name}: {'ok' if ok else 'FAILED'}")

    else:
        print(f"Unknown theme action: {action}")
        return 1

    return 0


# ---------------------------------------------------------------------------
# settings.local.json hook management
# ---------------------------------------------------------------------------

def _get_self_cmd() -> str:
    """Return the absolute path to the installed geekmagic_hook executable.

    Works cross-platform (Mac, Linux, Windows):
    - pipx / pip install  → shutil.which() finds the console-script wrapper
    - direct invocation   → sys.argv[0] resolved to absolute path
    """
    found = shutil.which("geekmagic_hook")
    if found:
        return str(pathlib.Path(found).resolve())
    return str(pathlib.Path(sys.argv[0]).resolve())


def _load_settings(path: pathlib.Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _save_settings(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _register_hooks(path: pathlib.Path) -> None:
    data = _load_settings(path)
    hooks = data.setdefault("hooks", {})

    cmd_base = _get_self_cmd()
    for event in HOOK_EVENTS:
        cmd = f"{cmd_base} --event {event}"
        entry = {"matcher": "", "hooks": [{"type": "command", "command": cmd}]}
        existing = hooks.setdefault(event, [])
        # Avoid duplicate registration
        if not any(
            h.get("hooks", [{}])[0].get("command", "") == cmd
            for h in existing
            if h.get("hooks")
        ):
            existing.append(entry)
        print(f"  ✓ {event}")

    _save_settings(path, data)


def _is_our_hook(command: str) -> bool:
    """Return True if the hook command belongs to geekmagic_hook (any install path)."""
    exe = pathlib.Path(command.split()[0]).name
    return exe in ("geekmagic_hook", "geekmagic_hook.exe")


def _unregister_hooks(path: pathlib.Path) -> None:
    data = _load_settings(path)
    hooks = data.get("hooks", {})

    for event in HOOK_EVENTS:
        if event not in hooks:
            continue
        hooks[event] = [
            h for h in hooks[event]
            if not any(
                _is_our_hook(e.get("command", ""))
                for e in h.get("hooks", [])
            )
        ]
        if not hooks[event]:
            del hooks[event]
        print(f"  ✗ {event}")

    if not hooks:
        data.pop("hooks", None)

    _save_settings(path, data)


def _get_registered_hooks(path: pathlib.Path) -> list[str]:
    data = _load_settings(path)
    registered = []
    for event, entries in data.get("hooks", {}).items():
        if any(
            _is_our_hook(e.get("command", ""))
            for h in entries
            for e in h.get("hooks", [])
        ):
            registered.append(event)
    return registered


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="GeekMagic display controller for Claude Code hooks"
    )
    parser.add_argument(
        "--event",
        metavar="EVENT",
        help="Hook event name (hook execution mode)",
        choices=HOOK_EVENTS,
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["setup", "uninstall", "status", "test", "discover", "logs", "theme"],
        help="Management command",
    )
    parser.add_argument("extra", nargs="*", help="Additional arguments for subcommands")
    parser.add_argument("--rescan", action="store_true", help="Force network rescan during setup")
    parser.add_argument("--lines", type=int, default=50, help="Lines to show in logs command")

    args = parser.parse_args()

    # Hook execution mode
    if args.event:
        return cmd_event(args.event)

    # Management commands
    cmd = args.command
    if cmd == "setup":
        return cmd_setup(rescan=args.rescan)
    elif cmd == "uninstall":
        return cmd_uninstall()
    elif cmd == "status":
        return cmd_status()
    elif cmd == "discover":
        return cmd_discover()
    elif cmd == "test":
        return cmd_test()
    elif cmd == "logs":
        return cmd_logs(lines=args.lines)
    elif cmd == "theme":
        if not args.extra:
            print("Usage: theme <list|upload> [args]")
            return 1
        return cmd_theme(args.extra[0], args.extra[1:])
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
