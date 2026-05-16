# geekmagic-hook

> Show your **Claude Code** working state on a **GeekMagic SmallTV-Ultra** pixel display — in real time, via Claude Code hooks.

## What it does

Every time Claude Code changes state (thinking, using a tool, waiting, rate-limited, done), a matching GIF plays on your GeekMagic display automatically.

| Claude Code State | GIF shown |
|-------------------|-----------|
| Session first start | `starting.gif` |
| Prompt received (subsequent) | `prompt_received.gif` |
| Calling a tool (Bash, Read, Edit…) | `calling_tools.gif` |
| Tool finished, still working | `working.gif` |
| Subagent completed | `working.gif` |
| Idle — waiting for next prompt | `waiting.gif` |
| Waiting for your permission | `permission.gif` |
| Rate-limited | `rate_limited.gif` |

## Requirements

- [GeekMagic SmallTV-Ultra](https://github.com/ClockworkSoul007/SmallTV-Pro) on the same Wi-Fi network
- [Claude Code](https://claude.ai/code) CLI
- Python 3.9+
- [pipx](https://pipx.pypa.io) (recommended) or pip

## Quick Start

```bash
# 1. Install
pipx install git+https://github.com/litdemon/geekmagic-hook

# 2. Auto-discover device, upload GIFs, register hooks
geekmagic_hook setup

# 3. Restart Claude Code — done!
```

Or with pip:

```bash
pip install git+https://github.com/litdemon/geekmagic-hook
geekmagic_hook setup
```

## CLI Reference

```bash
geekmagic_hook setup              # discover device + register Claude Code hooks
geekmagic_hook uninstall          # remove all hooks
geekmagic_hook status             # device info + hook registration status
geekmagic_hook test               # cycle through all states visually (2s each)
geekmagic_hook discover           # re-scan network (useful after IP change)
geekmagic_hook logs               # tail the hook log
geekmagic_hook theme list         # list GIFs on device
geekmagic_hook theme upload <dir> # upload a custom theme folder
```

See [`geekmagic_hook/README.md`](geekmagic_hook/README.md) for full documentation.

## Creating Custom GIF Themes

```bash
# Requires: pip install "imageio[pyav]" Pillow
cd gif
python3 convert_to_gif.py -i ./my_videos -o ./my_theme

geekmagic_hook theme upload ./my_theme
```

GIFs must be **240×240 px**. See [`gif/README.md`](gif/README.md).

## How It Works

`geekmagic_hook` registers itself in `~/.claude/settings.json` as a hook command for all Claude Code hook events. When Claude Code fires a hook, the script reads the event (and stdin JSON payload for `Notification`), then calls the GeekMagic HTTP API to switch the display GIF.

```
Claude Code  →  hook event  →  geekmagic_hook  →  HTTP GET /set?img=…  →  GeekMagic
```

Key design decisions:
- **Offline-safe**: 1.5 s HTTP timeout, exits 0 on failure — never blocks Claude
- **Dedup**: state tracked in `~/.geekmagic_hook/state.json` to skip redundant API calls
- **No dependencies**: stdlib only (`urllib`, `json`, `socket`, `threading`, …)
- **Cross-platform**: works on Mac, Linux, and Windows

## Project Structure

```
geekmagic-hook/
├── pyproject.toml               # Package metadata (pip/pipx installable)
├── geekmagic_hook/
│   ├── geekmagic_hook.py        # Single-file Python app (stdlib only)
│   └── themes/
│       └── default/             # Bundled GIF set (6 animations)
├── gif/
│   ├── convert_to_gif.py        # Video → 240x240 GIF converter
│   └── *.mov                    # Source animations
└── docs/
    └── protocol.md              # GeekMagic HTTP API reference
```

## GeekMagic HTTP API

Full API reference: [`docs/protocol.md`](docs/protocol.md)

Quick reference:

```bash
# Set display GIF (Photo Album mode = theme 3)
curl "http://DEVICE_IP/set?theme=3"
curl "http://DEVICE_IP/set?img=/image//working.gif"

# Check free space
curl "http://DEVICE_IP/space.json"
```

## License

MIT — see [LICENSE](LICENSE)
