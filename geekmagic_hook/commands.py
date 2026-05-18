"""CLI command implementations — each cmd_* function maps to one CLI sub-command."""

import logging
import pathlib
import shutil
import sys
import time

from .config import AppConfig, HookState
from .constants import (
    BUNDLE_THEMES_DIR,
    CONFIG_FILE,
    DEFAULT_THEME,
    HOME_DIR,
    LOG_FILE,
    SETTINGS_HOOKS,
    SETTINGS_LOCAL,
    THEMES_DIR,
)
from .device import GeekMagic
from .discovery import DeviceDiscovery
from .display import DisplayController
from .hook_manager import HookManager
from .logging_config import setup_logging

log = logging.getLogger("geekmagic_hook")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prompt(msg: str, default: str = "") -> str:
    """input() wrapper that handles EOF gracefully (non-interactive environments)."""
    try:
        return input(msg).strip()
    except EOFError:
        return default


# ---------------------------------------------------------------------------
# Hook execution
# ---------------------------------------------------------------------------

def cmd_event(event: str) -> int:
    """Hook execution mode — called by Claude Code for each hook event."""
    setup_logging()

    cfg = AppConfig()
    ip = cfg.get("device_ip")
    if not ip:
        log.debug("No device configured, skipping hook %s", event)
        return 0

    gm = GeekMagic(ip)
    if not gm.is_online():
        log.info("Device %s offline, skipping hook %s", ip, event)
        return 0

    ctrl = DisplayController(gm, cfg)
    hook_state = HookState()

    # Determine target state
    if event == "Notification":
        stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
        state = ctrl.parse_notification(stdin_data)
        if state is None:
            log.debug("Notification ignored (not rate-limited)")
            return 0
    elif event == "UserPromptSubmit":
        # First prompt in a fresh session → starting.gif; subsequent → prompt_received.gif
        state = "starting" if hook_state.current is None else "prompt_received"
    else:
        state = DisplayController.EVENT_STATES.get(event, "working")

    # Skip redundant API calls
    if hook_state.current == state:
        log.debug("State unchanged (%s), skipping API call", state)
        return 0

    ctrl.show(state)
    hook_state.update(state, event)
    return 0


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def cmd_setup(rescan: bool = False) -> int:
    """Discover device, upload GIFs, and register Claude Code hooks."""
    setup_logging(verbose=True)
    HOME_DIR.mkdir(parents=True, exist_ok=True)

    manager = HookManager()

    # [1/5] Install binary via pip
    print("\n[1/5] Installing geekmagic_hook via pip…")
    installed = manager.install_binary()
    if installed:
        print(f"  ✓ {installed}")
        in_path = shutil.which("geekmagic_hook")
        if not in_path:
            print(f"  ⚠ Add {installed.parent} to your PATH")
            print(f"    e.g. export PATH=\"{installed.parent}:$PATH\"")
    else:
        print("  ⚠ pip install failed — will use current invocation path")

    cfg = AppConfig()
    ip = cfg.get("device_ip")

    # [2/5] Device discovery
    print("\n[2/5] Searching for GeekMagic device…")
    if ip and not rescan:
        gm = GeekMagic(ip)
        if gm.is_online():
            print(f"  Using saved device at {ip}")
        else:
            print(f"  Saved device {ip} not responding, scanning…")
            ip = None

    if not ip:
        found = DeviceDiscovery().discover()
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

    print(f"\n  Device: {ip}  {info.get('m', '')} {info.get('v', '')}")
    print(f"  Free space: {free_kb} KB")

    # [3/5] Hook registration permission
    print("\n[3/5] Claude Code hook registration")
    if not SETTINGS_LOCAL.parent.exists():
        print(f"  Warning: {SETTINGS_LOCAL.parent} not found (is Claude Code installed?)")

    answer = _prompt(f"  Register hooks in {SETTINGS_HOOKS}? [y/N] ").lower()
    if answer != "y":
        print("Aborted.")
        return 0

    # [4/5] GIF upload
    print("\n[4/5] Uploading GIFs to device…")
    src_dir = BUNDLE_THEMES_DIR / DEFAULT_THEME
    dest_themes = THEMES_DIR / DEFAULT_THEME
    dest_themes.mkdir(parents=True, exist_ok=True)

    upload_dir = cfg.get("upload_dir", "/image/")
    for gif in src_dir.glob("*.gif"):
        dest = dest_themes / gif.name
        if not dest.exists():
            shutil.copy2(gif, dest)
        ok = gm.upload_gif(upload_dir, gif)
        print(f"  {gif.name}: {'ok' if ok else 'FAILED'}")

    # [5/5] Hook registration
    print(f"\n[5/5] Registering hooks in {SETTINGS_HOOKS}…")
    manager.register()

    cfg.set("device_ip", ip)
    cfg.save()

    print("\n✓ Setup complete. Restart Claude Code for hooks to take effect.")
    return 0


# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------

def cmd_uninstall() -> int:
    """Remove all geekmagic_hook hooks from settings.json."""
    setup_logging(verbose=True)
    print(f"Removing hooks from {SETTINGS_HOOKS}…")
    HookManager().unregister()
    print("✓ Hooks removed. Restart Claude Code for changes to take effect.")
    return 0


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def cmd_status() -> int:
    """Show device status and hook registration."""
    setup_logging(verbose=True)
    cfg = AppConfig()
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
            print(f"  Model:       {info.get('m', '')} {info.get('v', '')}")
            print(f"  Free space:  {free_kb}/{total_kb} KB")
            print(f"  GM Theme:    {active}")
    else:
        print("Device IP:     (not configured — run 'setup')")

    print()

    registered = HookManager().get_registered()
    if registered:
        print(f"Registered hooks ({len(registered)}):")
        for ev in registered:
            print(f"  ✓ {ev}")
    else:
        print("No hooks registered (run 'setup' to register)")

    hook_state = HookState()
    state_data = hook_state.to_dict()
    if state_data.get("current"):
        ts = state_data.get("ts", 0)
        age = int(time.time() - ts)
        print(
            f"\nLast state: {state_data['current']}"
            f"  ({age}s ago via {state_data.get('event', '')})"
        )

    return 0


# ---------------------------------------------------------------------------
# Discover
# ---------------------------------------------------------------------------

def cmd_discover() -> int:
    """Re-scan the network and update the saved device IP."""
    setup_logging(verbose=True)
    print("Scanning network…")
    found = DeviceDiscovery().discover()
    if not found:
        print("No GeekMagic devices found.")
        return 1

    for ip, info in found:
        print(f"  {ip}  {info.get('m', '')}  {info.get('v', '')}")

    cfg = AppConfig()
    if len(found) == 1:
        ip, _ = found[0]
        answer = _prompt(f"Update config to use {ip}? [y/N] ").lower()
        if answer == "y":
            cfg.set("device_ip", ip)
            cfg.save()
            print(f"✓ Config updated: device_ip = {ip}")
    else:
        ips = [ip for ip, _ in found]
        choice = _prompt(f"Choose device [{', '.join(ips)}]: ")
        if choice in ips:
            cfg.set("device_ip", choice)
            cfg.save()
            print(f"✓ Config updated: device_ip = {choice}")

    return 0


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def cmd_test() -> int:
    """Cycle through all display states for visual verification (2s each)."""
    setup_logging(verbose=True)
    cfg = AppConfig()
    ip = cfg.get("device_ip")
    if not ip:
        print("No device configured. Run 'setup' first.")
        return 1

    gm = GeekMagic(ip)
    if not gm.is_online():
        print(f"Device {ip} is offline.")
        return 1

    ctrl = DisplayController(gm, cfg)
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
        ctrl.show(state)
        print("✓")
        time.sleep(2)

    print("✓ Test complete.")
    return 0


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

def cmd_logs(lines: int = 50) -> int:
    """Print the last N lines of the hook log."""
    if not LOG_FILE.exists():
        print(f"No log file at {LOG_FILE}")
        return 0
    text = LOG_FILE.read_text().splitlines()
    for line in text[-lines:]:
        print(line)
    return 0


# ---------------------------------------------------------------------------
# Theme management
# ---------------------------------------------------------------------------

def cmd_theme(action: str, args: list[str]) -> int:
    """List GIFs on device or upload a custom theme directory."""
    setup_logging(verbose=True)
    cfg = AppConfig()

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
