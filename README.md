# GeekMagic Claude Status Display

> Show your **Claude Code** working state on a **GeekMagic SmallTV-Ultra** pixel display — in real time, via Claude Code hooks.

![Demo placeholder](docs/demo.gif)

## What it does

Every time Claude Code changes state (thinking, using a tool, waiting, rate-limited, done), a matching GIF plays on your GeekMagic display automatically.

| Claude Code State | Display |
|-------------------|---------|
| Session start / prompt received | `starting.gif` |
| Calling a tool (Bash, Read, Edit…) | `requesting.gif` |
| Tool finished, still working | `working.gif` |
| Subagent completed | `working.gif` |
| Waiting for your permission | `waiting.gif` |
| Rate-limited | `rate_limit.gif` |
| Claude stopped / idle | Time clock (GeekMagic theme 3) |

## Requirements

- [GeekMagic SmallTV-Ultra](https://github.com/ClockworkSoul007/SmallTV-Pro) on the same Wi-Fi network
- [Claude Code](https://claude.ai/code) CLI
- Python 3.9+

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/GeekMagic.git
cd GeekMagic

# 2. Install the hook app
cd geekmagic_hook
make install

# 3. Auto-discover device and register hooks
geekmagic_hook setup

# 4. Restart Claude Code — done!
```

## Project Structure

```
GeekMagic/
├── geekmagic_hook/          # Claude Code hook app (main tool)
│   ├── geekmagic_hook.py    # Single-file Python app (stdlib only)
│   ├── Makefile             # install / uninstall / clean
│   └── themes/
│       └── default/         # Bundled GIF set (6 animations)
├── gif/
│   ├── convert_to_gif.py    # Video → 240x240 GIF converter
│   ├── *.mov                # Source animations
│   └── output/              # Generated GIFs
└── docs/
    └── protocol.md          # GeekMagic HTTP API reference
```

## geekmagic_hook CLI

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
cd gif
pip install "imageio[pyav]" Pillow
python3 convert_to_gif.py -i ./my_videos -o ./my_theme

geekmagic_hook theme upload ./my_theme
```

GIFs must be **240×240 px**. See [`gif/README.md`](gif/README.md).

## How It Works

`geekmagic_hook` registers itself in `~/.claude/settings.local.json` as a hook command for all Claude Code hook events. When Claude Code fires a hook, the script reads the event (and stdin JSON payload for `Notification`), then calls the GeekMagic HTTP API to switch the display GIF.

```
Claude Code  →  hook event  →  geekmagic_hook  →  HTTP GET /set?img=…  →  GeekMagic
```

Key design decisions:
- **Offline-safe**: 1.5 s HTTP timeout, exits 0 on failure — never blocks Claude
- **Dedup**: state tracked in `~/.geekmagic_hook/state.json` to skip redundant API calls
- **No dependencies**: stdlib only (`urllib`, `json`, `socket`, `threading`, …)
- **Hooks in `settings.local.json`**: keeps personal paths out of version control

## GeekMagic HTTP API

Full API reference: [`docs/protocol.md`](docs/protocol.md)

Quick reference:

```bash
# Set display GIF
curl "http://DEVICE_IP/set?img=/image//working.gif"

# Switch to time clock
curl "http://DEVICE_IP/set?theme=3"

# Check free space
curl "http://DEVICE_IP/space.json"
```

## License

MIT — see [LICENSE](LICENSE)
