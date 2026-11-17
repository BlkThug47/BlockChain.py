"""Shared test fixtures: a low difficulty keeps mining instant."""
from pychain.blockchain import Blockchain
from pychain.transaction import Transaction
from pychain.wallet import Wallet

TEST_DIFFICULTY = 2


def make_chain() -> Blockchain:
    return Blockchain(difficulty=TEST_DIFFICULTY)


def signed_tx(sender: Wallet, recipient: str, amount: float) -> Transaction:
    tx = Transaction(sender.address, recipient, amount)
    tx.sign(sender)
    return tx
