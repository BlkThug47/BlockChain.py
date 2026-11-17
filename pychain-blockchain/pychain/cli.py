"""Command-line interface for PyChain."""
import argparse
import sys
from datetime import datetime
from pathlib import Path

from . import config, storage
from .exceptions import PyChainError
from .logger import get_logger, setup_logging
from .transaction import Transaction
from .wallet import Wallet

log = get_logger("cli")


# --- helpers ---------------------------------------------------------------
def _wallet_path(name: str) -> Path:
    return config.wallet_dir() / f"{name}.pem"


def _load_wallet(name: str) -> Wallet:
    path = _wallet_path(name)
    if not path.exists():
        raise PyChainError(f"Wallet '{name}' not found. Create it with: wallet create {name}")
    return Wallet.load(path)


def _resolve_address(name_or_address: str) -> str:
    """Accept either a wallet name or a raw address."""
    path = _wallet_path(name_or_address)
    return Wallet.load(path).address if path.exists() else name_or_address


def _fmt_time(ts: float) -> str:
    return "genesis" if ts == 0 else datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


# --- commands --------------------------------------------------------------
def cmd_wallet_create(args):
    path = _wallet_path(args.name)
    if path.exists():
        raise PyChainError(f"Wallet '{args.name}' already exists")
    wallet = Wallet()
    wallet.save(path)
    print(f"Created wallet '{args.name}'\n  address: {wallet.address}")


def cmd_wallet_list(args):
    paths = sorted(config.wallet_dir().glob("*.pem"))
    if not paths:
        print("No wallets yet. Create one with: wallet create <name>")
    for path in paths:
        print(f"{path.stem:<12} {Wallet.load(path).address}")


def cmd_balance(args):
    chain = storage.load_chain()
    address = _resolve_address(args.wallet)
    print(f"{args.wallet}: {chain.get_balance(address)} coins "
          f"({chain.get_balance(address, include_pending=True)} after pending)")


def cmd_send(args):
    chain = storage.load_chain()
    wallet = _load_wallet(args.sender)
    tx = Transaction(wallet.address, _resolve_address(args.recipient), args.amount)
    tx.sign(wallet)
    chain.add_transaction(tx)
    storage.save_chain(chain)
    print(f"Transaction {tx.tx_id[:12]}... queued ({args.amount} coins). "
          "Run 'mine' to confirm it.")


def cmd_mine(args):
    chain = storage.load_chain()
    miner = _load_wallet(args.miner)
    print(f"Mining block {len(chain.chain)} (difficulty {chain.difficulty})...")
    block = chain.mine_pending(miner.address)
    storage.save_chain(chain)
    print(f"Mined block {block.index}: nonce={block.nonce} hash={block.hash[:20]}... "
          f"({len(block.transactions)} tx, reward -> {args.miner})")


def cmd_pending(args):
    chain = storage.load_chain()
    if not chain.pending:
        print("No pending transactions.")
    for tx in chain.pending:
        print(f"{tx.tx_id[:12]}  {tx.sender[:10]}.. -> {tx.recipient[:10]}..  {tx.amount}")


def cmd_chain(args):
    chain = storage.load_chain()
    for block in chain.chain:
        print(f"Block #{block.index}  [{_fmt_time(block.timestamp)}]")
        print(f"  hash:     {block.hash}")
        print(f"  previous: {block.previous_hash}")
        print(f"  nonce:    {block.nonce}   merkle: {block.merkle_root[:16]}...")
        for tx in block.transactions:
            sender = "COINBASE" if tx.is_coinbase else tx.sender[:10] + ".."
            print(f"    {sender} -> {tx.recipient[:10]}..  {tx.amount}")


def cmd_validate(args):
    chain = storage.load_chain()
    ok, reason = chain.is_valid()
    print(("VALID: " if ok else "INVALID: ") + reason)
    log.info("Manual validation: %s (%s)", ok, reason)
    return 0 if ok else 1


def cmd_reset(args):
    if not args.yes:
        raise PyChainError("Refusing to delete the chain without --yes")
    for suffix in ("", ".bak"):
        path = Path(str(config.chain_file()) + (suffix if suffix else ""))
        path.unlink(missing_ok=True)
    log.warning("Chain data deleted by user")
    print("Chain data deleted (wallets and logs kept).")


def cmd_demo(args):
    """Create wallets, make transactions, mine blocks and validate - end to end."""
    for name in ("alice", "bob", "miner"):
        if not _wallet_path(name).exists():
            Wallet().save(_wallet_path(name))
    chain = storage.load_chain()
    alice, bob, miner = (_load_wallet(n) for n in ("alice", "bob", "miner"))

    print("1) Mining a block so Alice earns the reward...")
    chain.mine_pending(alice.address)
    print("2) Alice sends 20 to Bob, 5 to Miner...")
    for recipient, amount in ((bob, 20), (miner, 5)):
        tx = Transaction(alice.address, recipient.address, amount)
        tx.sign(alice)
        chain.add_transaction(tx)
    print("3) Miner confirms the transactions...")
    chain.mine_pending(miner.address)
    storage.save_chain(chain)

    for name, w in (("alice", alice), ("bob", bob), ("miner", miner)):
        print(f"   {name:<6} balance: {chain.get_balance(w.address)}")
    ok, reason = chain.is_valid()
    print(f"4) Validation: {reason}")
    print("\nInspect the result with:  python main.py chain")
    return 0 if ok else 1


# --- parser ----------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pychain", description="A small proof-of-work blockchain.")
    parser.add_argument("-v", "--verbose", action="store_true", help="show INFO logs in the console")
    sub = parser.add_subparsers(dest="command", required=True)

    wallet = sub.add_parser("wallet", help="manage wallets").add_subparsers(dest="action", required=True)
    create = wallet.add_parser("create", help="create a new wallet")
    create.add_argument("name")
    create.set_defaults(func=cmd_wallet_create)
    wallet.add_parser("list", help="list wallets").set_defaults(func=cmd_wallet_list)

    p = sub.add_parser("balance", help="show a wallet's balance")
    p.add_argument("wallet", help="wallet name or address")
    p.set_defaults(func=cmd_balance)

    p = sub.add_parser("send", help="create and queue a signed transaction")
    p.add_argument("sender", help="sender wallet name")
    p.add_argument("recipient", help="recipient wallet name or address")
    p.add_argument("amount", type=float)
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("mine", help="mine pending transactions into a new block")
    p.add_argument("miner", help="wallet name that receives the reward")
    p.set_defaults(func=cmd_mine)

    sub.add_parser("pending", help="list pending transactions").set_defaults(func=cmd_pending)
    sub.add_parser("chain", help="print the whole chain").set_defaults(func=cmd_chain)
    sub.add_parser("validate", help="audit the chain's integrity").set_defaults(func=cmd_validate)

    p = sub.add_parser("reset", help="delete the stored chain")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_reset)

    sub.add_parser("demo", help="run an end-to-end demonstration").set_defaults(func=cmd_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(verbose=args.verbose)
    log.info("Command: %s", " ".join(argv if argv is not None else sys.argv[1:]))
    try:
        return args.func(args) or 0
    except PyChainError as exc:
        log.error("%s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1
