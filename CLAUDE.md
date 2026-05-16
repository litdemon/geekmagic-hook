# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`geekmagic-hook` is a Claude Code hook executor that drives a **GeekMagic SmallTV-Ultra** pixel display (240×240). When Claude Code changes state (thinking, calling a tool, waiting, etc.), the corresponding GIF plays on the display via the device's HTTP API.

## Key Commands

```bash
# Install locally for development (requires pip ≥ 22 for pyproject.toml editable installs)
pip install -e .

# Or install from GitHub
pipx install git+https://github.com/litdemon/geekmagic-hook

# Setup: discover device, upload GIFs, register Claude Code hooks
geekmagic_hook setup

# Cycle through all 7 states visually (2s each) — primary dev verification
geekmagic_hook test

# After editing geekmagic_hook.py locally, the running binary must be refreshed:
cp geekmagic_hook/geekmagic_hook.py ~/.geekmagic_hook/geekmagic_hook

# Convert .mov source files → 240×240 GIFs (requires imageio[pyav] + Pillow)
cd gif
python3 convert_to_gif.py ./default -o ../geekmagic_hook/themes/default
```

## Architecture

### Single-file app: `geekmagic_hook/geekmagic_hook.py`

All logic lives in one stdlib-only Python file. Sections in order:

1. **Paths** — `HOME_DIR = ~/.geekmagic_hook/`, `CONFIG_FILE`, `STATE_FILE`, `LOG_FILE`, `SETTINGS_HOOKS = ~/.claude/settings.json`
2. **Config / State** — `load_config()` / `save_config()`, `load_state()` / `save_state()`. Config stores device IP and active theme; state stores `{"current": <state_name>}` for dedup.
3. **`GeekMagic` class** — thin HTTP wrapper around the device API. Key methods:
   - `set_auto_switch(enabled)` — reads `/theme_list.json` first; skips the API call if `sw_en` already matches (prevents a firmware side-effect where re-sending `theme_list` briefly activates the first theme in the list, e.g. Weather Clock Today).
   - `set_theme(3)` — switches to Photo Album mode (required before `set_image`).
   - `set_image("/image//file.gif")` — double-slash path format is what the device filelist uses.
4. **Network discovery** — `discover_devices()` scans the local subnet with 254 threads in parallel (0.8s timeout each).
5. **Hook state → display** — `EVENT_STATES`, `_gif_name_for()`, `_parse_notification()`, `_display_state()`.
6. **Commands** — `cmd_event()`, `cmd_setup()`, `cmd_test()`, `cmd_status()`, `cmd_uninstall()`, `cmd_discover()`, `cmd_logs()`, `cmd_theme()`.

### Hook execution flow

```
Claude Code fires hook event
  → geekmagic_hook --event <EventName>   (registered in ~/.claude/settings.json)
  → cmd_event()
      → parse state (Notification reads stdin JSON)
      → dedup: skip if state.json["current"] == state
      → _display_state(): set_auto_switch(False) → set_theme(3) → set_image()
      → save_state()
```

### State → GIF mapping

| State | GIF | Trigger |
|-------|-----|---------|
| `starting` | `starting.gif` | First `UserPromptSubmit` (no prior state) |
| `prompt_received` | `prompt_received.gif` | Subsequent `UserPromptSubmit` |
| `calling_tools` | `calling_tools.gif` | `PreToolUse` |
| `working` | `working.gif` | `PostToolUse`, `SubagentStop` |
| `idle` | `waiting.gif` | `Stop` |
| `permission` | `permission.gif` | `Notification` with permission keywords |
| `rate_limited` | `rate_limited.gif` | `Notification` with rate/limit/429 keywords |

### Important constraints

- **stdlib only** — no third-party dependencies in `geekmagic_hook.py`.
- **HTTP timeout 1.5s** — hooks must never block Claude Code; all failures exit 0.
- **Hooks must be in `~/.claude/settings.json`** (not `settings.local.json`).
- **Installed binary vs source**: hooks call `~/.geekmagic_hook/geekmagic_hook` (the file registered at `setup` time). Editing `geekmagic_hook/geekmagic_hook.py` does **not** automatically update it — you must `cp` or re-run `setup`.

## File Layout

```
geekmagic_hook/
  geekmagic_hook.py          # entire application
  themes/default/            # 7 bundled GIFs (240×240)
gif/
  default/                   # source .mov files for the default theme
  convert_to_gif.py          # video → GIF converter (needs imageio[pyav], Pillow)
docs/protocol.md             # GeekMagic HTTP API reference
pyproject.toml               # pip/pipx package (entry point: geekmagic_hook)
```

## GeekMagic Device API Quick Reference

Base URL: `http://<device_ip>` (no auth). See `docs/protocol.md` for full reference.

```bash
GET  /v.json                          # device info (used for online check)
GET  /app.json                        # current active theme number
GET  /theme_list.json                 # auto-switch config: {list, sw_en, sw_i}
GET  /set?theme=3                     # switch to Photo Album mode
GET  /set?img=/image//file.gif        # set displayed image (double-slash path)
GET  /set?theme_list=...&sw_en=0&theme_interval=N  # toggle auto-switch
POST /doUpload?dir=/image/            # upload GIF (multipart/form-data)
GET  /filelist?dir=/image/            # list uploaded files (HTML table)
GET  /space.json                      # storage: {total, free} bytes
```

Theme numbers: 0=Weather Clock Today, 1=Weather Forecast, 2=Simple Weather Clock, **3=Photo Album**, 4–6=Time Styles.
