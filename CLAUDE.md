# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`geekmagic-hook` is a Claude Code hook executor that drives a **GeekMagic SmallTV-Ultra** pixel display (240×240). When Claude Code changes state (thinking, calling a tool, waiting, etc.), the corresponding GIF plays on the display via the device's HTTP API.

## Key Commands

```bash
# Install in editable mode for development
pip install -e .

# Or install from GitHub
pipx install git+https://github.com/litdemon/geekmagic-hook

# Setup: discover device, upload GIFs, register Claude Code hooks (runs pip install internally)
geekmagic_hook setup

# Cycle through all 7 states visually (2s each) — primary dev verification
geekmagic_hook test

# Check version
geekmagic_hook --version

# Convert .mov source files → 240×240 GIFs (requires imageio[pyav] + Pillow)
cd gif && python3 convert_to_gif.py ./default -o ../geekmagic_hook/themes/default
```

After editing source, changes apply immediately via the editable install — no copy step needed.

## Architecture

### Module layout (`geekmagic_hook/`)

| Module | Class / Role |
|--------|-------------|
| `constants.py` | Paths (`HOME_DIR`, `CONFIG_FILE`, …), `HOOK_EVENTS`, timeouts |
| `logging_config.py` | `setup_logging(verbose)` — rotating file log + optional stderr |
| `config.py` | `AppConfig` (config.json r/w), `HookState` (state.json dedup) |
| `device.py` | `GeekMagic` — HTTP API client (all methods timeout at 1.5 s, exit 0 on failure) |
| `discovery.py` | `DeviceDiscovery` — 254-thread parallel subnet scan |
| `display.py` | `DisplayController` — event→state→GIF mapping, permission detection |
| `hook_manager.py` | `HookManager` — hook registration in settings.json, pip-based binary install |
| `commands.py` | `cmd_event()`, `cmd_setup()`, `cmd_test()`, … — CLI command implementations |
| `cli.py` | `main()` — argparse entry point (`geekmagic_hook.cli:main`) |

### Hook execution flow

```
Claude Code fires hook event
  → geekmagic_hook --event <EventName>   (registered in ~/.claude/settings.json)
  → cmd_event()  [commands.py]
      → read stdin for Notification / PreToolUse
      → determine state via DisplayController
      → dedup: skip if HookState.current == state
      → DisplayController.show(): set_auto_switch(False) → set_theme(3) → set_image()
      → HookState.update()
```

### State → GIF mapping

| Hook Event | State | GIF | Notes |
|------------|-------|-----|-------|
| `UserPromptSubmit` | `starting` | `starting.gif` | First prompt only (no prior state) |
| `UserPromptSubmit` | `prompt_received` | `prompt_received.gif` | Subsequent prompts |
| `PreToolUse` | `calling_tools` | `calling_tools.gif` | Tool in `permissions.allow` |
| `PreToolUse` | `permission` | `permission.gif` | Tool not in `permissions.allow` |
| `PostToolUse` | `working` | `working.gif` | |
| `Stop` | `idle` | `waiting.gif` | |
| `Notification` | `rate_limited` | `rate_limited.gif` | Message contains rate/limit/429 |
| `Notification` | `permission` | `permission.gif` | All other notifications |

### Key design constraints

- **stdlib only** in all `geekmagic_hook/` modules — no third-party deps.
- **HTTP timeout 1.5 s**, all failures exit 0 — hooks must never block Claude Code.
- **Hooks registered in `~/.claude/settings.json`** (not `settings.local.json`).
- **Binary location**: `setup` runs `pip install -e <project_root>` via subprocess. The installed script lands in the Python user-scripts dir (`sysconfig.get_path("scripts", "posix_user")` — e.g. `~/Library/Python/3.9/bin` on macOS, `~/.local/bin` on Linux). Falls back to writing a wrapper shim if pip fails.
- **`set_auto_switch()`** reads `/theme_list.json` first and skips the API call if `sw_en` is already in the desired state — avoids a firmware side-effect that briefly flashes the first theme in the rotation list.
- **`select_tools.gif`** exists in `themes/default/` but is not referenced in `STATE_GIF_MAP` — it is unused.

## GeekMagic Device API Quick Reference

Base URL: `http://<device_ip>` (no auth). See `docs/protocol.md` for full reference.

```bash
GET  /v.json                                        # device info / online check
GET  /set?theme=3                                   # switch to Photo Album mode (required before set_image)
GET  /set?img=/image//file.gif                      # display image (note double-slash)
GET  /set?theme_list=...&sw_en=0&theme_interval=N   # toggle auto-switch
POST /doUpload?dir=/image/                          # upload GIF (multipart/form-data)
GET  /filelist?dir=/image/                          # list uploaded files (HTML)
GET  /space.json                                    # {total, free} bytes
```

Theme numbers: 0=Weather Clock Today, 1=Weather Forecast, 2=Simple Weather Clock, **3=Photo Album**, 4–6=Time Styles.
