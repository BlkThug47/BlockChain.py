"""JSON persistence with atomic writes and a one-step backup."""
import json
import os
import shutil
from pathlib import Path

from . import config
from .blockchain import Blockchain
from .exceptions import InvalidChainError, StorageError
from .logger import get_logger

log = get_logger("storage")


def save_chain(blockchain: Blockchain, path: Path | None = None) -> Path:
    """Write the chain atomically (temp file + rename) and keep a ``.bak`` copy."""
    path = path or config.chain_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        if path.exists():
            shutil.copy2(path, path.with_suffix(".bak"))
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(blockchain.to_dict(), fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError as exc:
        raise StorageError(f"Could not save chain to {path}: {exc}") from exc
    log.debug("Chain saved to %s (%d blocks)", path, len(blockchain.chain))
    return path


def load_chain(path: Path | None = None) -> Blockchain:
    """Load and validate the chain; return a fresh one if no file exists."""
    path = path or config.chain_file()
    if not path.exists():
        log.info("No chain file at %s - starting a new chain", path)
        return Blockchain()
    try:
        with open(path, encoding="utf-8") as fh:
            blockchain = Blockchain.from_dict(json.load(fh))
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise StorageError(f"Could not read chain from {path}: {exc}") from exc

    ok, reason = blockchain.is_valid()
    if not ok:
        log.error("Loaded chain failed validation: %s", reason)
        raise InvalidChainError(reason)
    log.info("Chain loaded from %s (%d blocks)", path, len(blockchain.chain))
    return blockchain
