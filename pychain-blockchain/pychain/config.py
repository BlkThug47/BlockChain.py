"""Central configuration: paths and blockchain parameters.

Set the ``PYCHAIN_HOME`` environment variable to relocate the data, log and
wallet folders (the test-suite uses this to run in a temporary directory).
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def home() -> Path:
    return Path(os.environ.get("PYCHAIN_HOME", PROJECT_ROOT))


def data_dir() -> Path:
    return home() / "data"


def log_dir() -> Path:
    return home() / "logs"


def wallet_dir() -> Path:
    return home() / "wallets"


def chain_file() -> Path:
    return data_dir() / "chain.json"


# --- Blockchain parameters -------------------------------------------------
DIFFICULTY = 4          # number of leading zeros required in a block hash
MINING_REWARD = 50.0    # coins created for the miner of each block
COINBASE_SENDER = "SYSTEM"
GENESIS_PREVIOUS_HASH = "0" * 64
