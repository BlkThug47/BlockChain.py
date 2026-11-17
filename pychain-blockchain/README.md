# PyChain - a Proof-of-Work Blockchain in Python

A compact, fully tested blockchain written in Python. It implements the core
ideas behind Bitcoin-style ledgers: signed transactions, Merkle roots,
proof-of-work mining, mining rewards, balance tracking, full-chain validation,
persistent storage and structured logging - all driven from a command-line interface.

> Educational project. It is a single-node ledger (no networking or consensus
> between peers) and is **not** intended for real-world value.

## Features

| Area | What is implemented |
|------|---------------------|
| Blocks | Index, timestamp, previous-hash link, nonce, Merkle root of transactions |
| Proof of work | SHA-256 hash must start with `N` zeros (`DIFFICULTY` in `config.py`) |
| Transactions | ECDSA (secp256k1) signed, address derived from the public key |
| Wallets | Key generation, PEM storage, name-based lookups from the CLI |
| Rewards | Coinbase transaction pays the miner of every block |
| Validation | Hashes, links, PoW, signatures, reward amounts and balance replay (no overspending) |
| Storage | JSON file, atomic writes (temp file + rename), `.bak` backup, validated on load |
| Logging | Rotating log file with every command, transaction, block and error |
| Tests | 22 unit and end-to-end tests using only `unittest` |

## Project structure

```
pychain-blockchain/
├── README.md                  # this file
├── requirements.txt           # third-party dependencies (cryptography)
├── .gitignore                 # keeps runtime data out of git
├── main.py                    # entry point: python main.py <command>
│
├── pychain/                   # the application package
│   ├── __init__.py
│   ├── config.py              # paths, difficulty, mining reward
│   ├── exceptions.py          # custom error types
│   ├── logger.py              # rotating file logging setup
│   ├── wallet.py              # ECDSA keys, signing, verification
│   ├── transaction.py         # signed transfers + validation rules
│   ├── block.py               # block structure, Merkle root, mining
│   ├── blockchain.py          # chain, pending pool, balances, validation
│   ├── storage.py             # save/load chain (atomic JSON)
│   └── cli.py                 # argparse commands
│
├── tests/                     # unittest suite
│   ├── __init__.py
│   ├── helpers.py
│   ├── test_wallet.py
│   ├── test_blockchain.py
│   ├── test_storage.py
│   └── test_cli.py
│
├── data/                      # created at runtime
│   └── chain.json             # the blockchain (+ chain.bak backup)
├── logs/                      # created at runtime
│   └── pychain.log            # rotating log (1 MB x 3 backups)
└── wallets/                   # created at runtime
    └── <name>.pem             # private keys (never commit these)
```

## Getting started

**Requirements:** Python 3.10 or newer.

```bash
# 1. (optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. install the dependency
pip install -r requirements.txt

# 3. run the end-to-end demo
python main.py demo
```

## Usage

```bash
python main.py wallet create alice     # create wallets
python main.py wallet create bob
python main.py wallet list

python main.py mine alice              # mine a block; Alice earns 50 coins
python main.py send alice bob 20       # sign and queue a transaction
python main.py pending                 # view the transaction pool
python main.py mine alice              # confirm it in a new block

python main.py balance bob             # -> bob: 20.0 coins
python main.py chain                   # print every block
python main.py validate                # audit the whole chain
python main.py reset --yes             # delete chain data (keeps wallets and logs)
python main.py -v mine alice           # -v mirrors INFO logs to the console
```

Example output of `python main.py chain`:

```
Block #2  [2026-11-17 07:56:58]
  hash:     000073d63328a6f61f68715f1ba6ea693709627020c3abe319fef9621ca8c7e3
  previous: 00002f22478f7fccfa7b7a4ca4482a82ddca73051b4925f175c7e03956b87510
  nonce:    25094   merkle: e5dca98cfdb84d49...
    COINBASE -> ca6029c1f4..  50.0
    a7464f544b.. -> 724ef17678..  20
```

## Storage and logging

* **Chain data** - `data/chain.json` holds the difficulty, reward, every block and
  the pending pool. It is rewritten atomically after each state-changing command, and
  the previous version is copied to `chain.bak`. On load the chain is fully
  re-validated, so a tampered file is rejected instead of silently trusted.
* **Wallets** - `wallets/<name>.pem` (PKCS#8, unencrypted; a real system would encrypt these).
* **Logs** - `logs/pychain.log` records every command, accepted transaction, mined
  block (nonce, hash, duration), wallet creation, storage operation and error:

```
2026-11-17 07:56:58,754 | INFO  | pychain.blockchain | Block 1 mined in 0.13s nonce=17971 hash=00002f...
2026-11-17 07:56:58,757 | INFO  | pychain.blockchain | Transaction accepted d49e6afad596: a7464f544b -> 724ef17678 amount=20
```

Change the root folder for all three with the `PYCHAIN_HOME` environment variable.

## How it works

1. **Wallet** - a secp256k1 key pair. The address is `SHA-256(public key)[:40]`.
2. **Transaction** - sender, recipient, amount and timestamp are serialised canonically
   and signed. Nodes check the signature, that the public key matches the sender
   address, and that the sender can afford it (including already-pending spends).
3. **Block** - transactions are summarised by a Merkle root; the header
   (`index, timestamp, merkle_root, previous_hash, nonce`) is hashed with SHA-256.
4. **Mining** - the nonce is incremented until the hash has `DIFFICULTY` leading zeros.
   The first transaction of every block is the coinbase reward.
5. **Validation** - `Blockchain.is_valid()` re-computes every hash, checks links and
   proof of work, verifies all signatures and replays balances from genesis.

Editing any past block changes its hash, which breaks the link in the next block and
invalidates its proof of work. Demonstration:

```bash
# edit an amount in data/chain.json by hand, then:
python main.py validate
# INVALID: Block 2: hash does not match contents
```

## Running the tests

```bash
python -m unittest discover -s . -t . -v
```

## Design decisions

* **No global state** - `Blockchain` is a plain object; storage, CLI and logging are separate layers.
* **Dataclasses + type hints** for blocks and transactions.
* **Custom exceptions** (`InvalidTransactionError`, `InvalidChainError`, `StorageError`) so the CLI reports clean errors.
* **Config read at call time**, which lets the tests run in a temporary directory with low difficulty.

## Limitations and future work

* Peer-to-peer networking, a REST API (Flask/FastAPI) and longest-chain consensus
* Dynamic difficulty adjustment and block-size limits
* Encrypted wallet files and a UTXO model instead of account balances
* SQLite/LevelDB storage for large chains

## Licence

MIT - free to use and adapt.
