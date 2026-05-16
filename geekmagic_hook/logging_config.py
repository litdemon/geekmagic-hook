"""Logging setup for geekmagic_hook."""

import logging
import logging.handlers

from .constants import LOG_DIR, LOG_FILE


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure and return the root geekmagic_hook logger.

    Writes rotating logs to LOG_FILE; when verbose=True also streams to stderr.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("geekmagic_hook")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Avoid adding duplicate handlers on repeated calls
    if not logger.handlers:
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=1024 * 1024, backupCount=3
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)

    if verbose:
        has_stream = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
        if not has_stream:
            sh = logging.StreamHandler()
            sh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
            logger.addHandler(sh)

    return logger
