# geekmagic_hook

Single-file Python app that connects **Claude Code hooks** to a **GeekMagic SmallTV-Ultra** display.

## Installation

```bash
make install
# Copies geekmagic_hook.py to ~/.geekmagic_hook/geekmagic_hook and sets +x
```

Then run setup:

```bash
geekmagic_hook setup
```

`setup` will:
1. Scan your local network for a GeekMagic device
2. Show device info and ask for confirmation
3. Upload the bundled GIFs to the device
4. Register all hooks in `~/.claude/settings.local.json`

Restart Claude Code once to activate.

## Commands

### Management

| Command | Description |
|---------|-------------|
| `setup` | Discover device, upload GIFs, register hooks |
| `setup --rescan` | Force network re-scan even if IP is saved |
| `uninstall` | Remove all hooks from `settings.local.json` |
| `status` | Show device status, free space, registered hooks, last state |
| `test` | Cycle through all display states (2 s each) for visual verification |
| `discover` | Re-scan network and update saved device IP |
| `logs [--lines N]` | Print last N lines of `~/.geekmagic_hook/logs/hook.log` |
| `theme list` | List GIF files on device and local themes |
| `theme upload <dir>` | Upload all `.gif` files in a directory to the device |

### Hook execution (called by Claude Code)

```bash
# These are called automatically — you don't run them manually
geekmagic_hook --event UserPromptSubmit
geekmagic_hook --event PreToolUse
geekmagic_hook --event PostToolUse
geekmagic_hook --event Stop
geekmagic_hook --event Notification
geekmagic_hook --event SubagentStop
```

## File Layout

After `make install`, all runtime files live under `~/.geekmagic_hook/`:

```
~/.geekmagic_hook/
├── geekmagic_hook        # executable (copy of geekmagic_hook.py)
├── config.json           # device_ip, active_theme, upload_dir, …
├── state.json            # last displayed state (dedup guard)
├── themes/
│   └── default/
│       ├── starting.gif
│       ├── requesting.gif
│       ├── working.gif
│       ├── waiting.gif
│       ├── rate_limit.gif
│       └── subagent.gif
└── logs/
    └── hook.log          # rotating log (1 MB × 3)
```

## Hook → Display Mapping

| Hook Event | State | GIF shown |
|-----------|-------|-----------|
| `UserPromptSubmit` | STARTING | `starting.gif` |
| `PreToolUse` | REQUESTING | `requesting.gif` |
| `PostToolUse` | WORKING | `working.gif` |
| `SubagentStop` | WORKING | `working.gif` |
| `Notification` (rate limit) | RATE LIMITED | `rate_limit.gif` |
| `Notification` (permission) | WAITING | `waiting.gif` |
| `Stop` | IDLE | `waiting.gif` |

All states use Photo Album (image-only) mode — auto theme switching is disabled
while Claude Code is running. `Notification` type is detected by scanning the
`message` field in the hook's stdin JSON payload.

> **Note:** There is no hook for Claude Code process exit. The display remains
> on `waiting.gif` after the app closes. To restore the device's normal
> (auto-switching) mode, run `geekmagic_hook test` or adjust the display
> directly on the device.

## Custom Themes

A theme is a folder of `.gif` files. File names must match the state names above.

```
my_theme/
├── starting.gif
├── requesting.gif
├── working.gif
├── waiting.gif
├── rate_limit.gif
└── subagent.gif    # optional
```

Upload:

```bash
geekmagic_hook theme upload ./my_theme
```

Then update your config to use it:

```json
// ~/.geekmagic_hook/config.json
{
  "active_theme": "my_theme",
  "upload_dir": "/image/"
}
```

## settings.local.json (registered by setup)

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {"matcher": "", "hooks": [{"type": "command", "command": "~/.geekmagic_hook/geekmagic_hook --event UserPromptSubmit"}]}
    ],
    "PreToolUse": [
      {"matcher": "", "hooks": [{"type": "command", "command": "~/.geekmagic_hook/geekmagic_hook --event PreToolUse"}]}
    ],
    "PostToolUse": [
      {"matcher": "", "hooks": [{"type": "command", "command": "~/.geekmagic_hook/geekmagic_hook --event PostToolUse"}]}
    ],
    "Stop": [
      {"matcher": "", "hooks": [{"type": "command", "command": "~/.geekmagic_hook/geekmagic_hook --event Stop"}]}
    ],
    "Notification": [
      {"matcher": "", "hooks": [{"type": "command", "command": "~/.geekmagic_hook/geekmagic_hook --event Notification"}]}
    ],
    "SubagentStop": [
      {"matcher": "", "hooks": [{"type": "command", "command": "~/.geekmagic_hook/geekmagic_hook --event SubagentStop"}]}
    ]
  }
}
```

## Uninstall

```bash
make uninstall
# removes ~/.geekmagic_hook/geekmagic_hook and cleans hooks from settings.local.json
# config, logs, and theme files are preserved
```

To fully remove:

```bash
make uninstall
rm -rf ~/.geekmagic_hook
```
