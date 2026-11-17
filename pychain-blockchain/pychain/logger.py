"""Logging setup: everything goes to a rotating file; -v also mirrors INFO to the console."""
import logging
from logging.handlers import RotatingFileHandler

from . import config

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_configured = False


def setup_logging(verbose: bool = False) -> None:
    """Configure the root ``pychain`` logger once per process."""
    global _configured
    if _configured:
        return

    log_dir = config.log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("pychain")
    root.setLevel(logging.DEBUG)
    root.propagate = False

    file_handler = RotatingFileHandler(
        log_dir / "pychain.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO if verbose else logging.CRITICAL)  # errors are printed by the CLI
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"pychain.{name}")
