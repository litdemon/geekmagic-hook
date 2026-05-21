try:
    from importlib.metadata import version as _pkg_version
    __version__: str = _pkg_version("geekmagic-hook")
except Exception:
    __version__ = "1.3.0"  # fallback when running from source (not pip-installed)

from .cli import main

__all__ = ["__version__", "main"]
