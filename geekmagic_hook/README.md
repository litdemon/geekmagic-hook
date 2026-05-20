# geekmagic_hook

Python package that connects **Claude Code hooks** to a **GeekMagic SmallTV-Ultra** display.

## Installation

```bash
pipx install git+https://github.com/litdemon/geekmagic-hook
# or
pip install git+https://github.com/litdemon/geekmagic-hook
```

Then run setup:

```bash
geekmagic_hook setup
```

`setup` will:
1. Run `pip install -e .` to ensure the binary is on your PATH
2. Scan your local network for a GeekMagic device
3. Upload the bundled GIFs to the device
4. Register all hooks in `~/.claude/settings.json`

Restart Claude Code once to activate.

## Commands

### Management

| Command | Description |
|---------|-------------|
| `setup` | Discover device, upload GIFs, register hooks |
| `setup --rescan` | Force network re-scan even if IP is saved |
| `uninstall` | Remove all hooks from `settings.json` |
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
geekmagic_hook --event PermissionRequest
```

## File Layout

Runtime files live under `~/.geekmagic_hook/`:

```
~/.geekmagic_hook/
├── config.json           # device_ip, active_theme, upload_dir, …
├── state.json            # last displayed state (dedup guard)
├── themes/
│   └── default/
│       ├── starting.gif
│       ├── prompt_received.gif
│       ├── calling_tools.gif
│       ├── working.gif
│       ├── waiting.gif
│       ├── permission.gif
│       └── rate_limited.gif
└── logs/
    └── hook.log          # rotating log (1 MB × 3)
```

## Hook → Display Mapping

| Hook Event | State | GIF shown |
|-----------|-------|-----------|
| `UserPromptSubmit` (first) | starting | `starting.gif` |
| `UserPromptSubmit` (subsequent) | prompt\_received | `prompt_received.gif` |
| `PreToolUse` | calling\_tools | `calling_tools.gif` |
| `PostToolUse` | working | `working.gif` |
| `PermissionRequest` | permission | `permission.gif` |
| `Notification` (rate limit) | rate\_limited | `rate_limited.gif` |
| `Stop` | idle | `waiting.gif` |

All states use Photo Album (image-only) mode — auto theme switching is disabled
while Claude Code is running.

`PermissionRequest` fires only when Claude Code actually stops and waits for the
user to approve or deny a tool call — this is the only trigger for `permission.gif`.

`Notification` events that don't contain rate-limit keywords are silently ignored.

## Custom Themes

A theme is a folder of `.gif` files named after the states above (**240×240 px**).

```
my_theme/
├── starting.gif
├── prompt_received.gif
├── calling_tools.gif
├── working.gif
├── waiting.gif
├── permission.gif
└── rate_limited.gif
```

Upload:

```bash
geekmagic_hook theme upload ./my_theme
```

## Hooks registered by setup

```json
{
  "hooks": {
    "UserPromptSubmit":  [{"matcher": "", "hooks": [{"type": "command", "command": "geekmagic_hook --event UserPromptSubmit"}]}],
    "PreToolUse":        [{"matcher": "", "hooks": [{"type": "command", "command": "geekmagic_hook --event PreToolUse"}]}],
    "PostToolUse":       [{"matcher": "", "hooks": [{"type": "command", "command": "geekmagic_hook --event PostToolUse"}]}],
    "Stop":              [{"matcher": "", "hooks": [{"type": "command", "command": "geekmagic_hook --event Stop"}]}],
    "Notification":      [{"matcher": "", "hooks": [{"type": "command", "command": "geekmagic_hook --event Notification"}]}],
    "PermissionRequest": [{"matcher": "", "hooks": [{"type": "command", "command": "geekmagic_hook --event PermissionRequest"}]}]
  }
}
```

## Uninstall

```bash
geekmagic_hook uninstall
```

To fully remove all runtime data:

```bash
geekmagic_hook uninstall
rm -rf ~/.geekmagic_hook
```
