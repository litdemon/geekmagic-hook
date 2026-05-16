"""Command-line entry point for geekmagic_hook."""

import argparse
import sys

from .commands import (
    cmd_discover,
    cmd_event,
    cmd_logs,
    cmd_setup,
    cmd_status,
    cmd_test,
    cmd_theme,
    cmd_uninstall,
)
from . import __version__
from .constants import HOOK_EVENTS


def main() -> int:
    """Parse arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(
        description="GeekMagic display controller for Claude Code hooks",
        epilog=(
            "Examples:\n"
            "  geekmagic_hook setup              # discover device + register hooks\n"
            "  geekmagic_hook test               # cycle through all states visually\n"
            "  geekmagic_hook --event PreToolUse # hook execution mode (called by Claude Code)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"geekmagic_hook {__version__}",
    )
    parser.add_argument(
        "--event",
        metavar="EVENT",
        help="Hook event name (hook execution mode, called by Claude Code)",
        choices=HOOK_EVENTS,
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["setup", "uninstall", "status", "test", "discover", "logs", "theme"],
        help="Management command",
    )
    parser.add_argument(
        "extra",
        nargs="*",
        help="Additional arguments for sub-commands (e.g. theme upload <dir>)",
    )
    parser.add_argument(
        "--rescan",
        action="store_true",
        help="Force network re-scan during setup even if a device is already saved",
    )
    parser.add_argument(
        "--lines",
        type=int,
        default=50,
        help="Number of log lines to show (default: 50)",
    )

    args = parser.parse_args()

    # Hook execution mode (called by Claude Code)
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
