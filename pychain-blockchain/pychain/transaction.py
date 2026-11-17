"""Signed value transfers between addresses."""
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field

from . import config
from .exceptions import InvalidTransactionError
from .wallet import Wallet, address_from_public_key, verify_signature


@dataclass
class Transaction:
    sender: str
    recipient: str
    amount: float
    timestamp: float = field(default_factory=time.time)
    sender_public_key: str = ""
    signature: str = ""

    # --- identity ----------------------------------------------------------
    @property
    def is_coinbase(self) -> bool:
        return self.sender == config.COINBASE_SENDER

    def payload(self) -> str:
        """Canonical string that gets signed (excludes the signature itself)."""
        return json.dumps(
            {
                "sender": self.sender,
                "recipient": self.recipient,
                "amount": self.amount,
                "timestamp": self.timestamp,
                "sender_public_key": self.sender_public_key,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @property
    def tx_id(self) -> str:
        return hashlib.sha256((self.payload() + self.signature).encode()).hexdigest()

    # --- signing & validation ---------------------------------------------
    def sign(self, wallet: Wallet) -> None:
        if wallet.address != self.sender:
            raise InvalidTransactionError("Wallet does not own the sender address")
        self.sender_public_key = wallet.public_key_hex
        self.signature = wallet.sign(self.payload())

    def validate(self) -> None:
        """Raise ``InvalidTransactionError`` if the transaction is not valid."""
        if self.amount <= 0:
            raise InvalidTransactionError("Amount must be positive")
        if not self.recipient:
            raise InvalidTransactionError("Recipient is required")
        if self.is_coinbase:
            if self.signature:
                raise InvalidTransactionError("Coinbase transactions are unsigned")
            return
        if self.sender == self.recipient:
            raise InvalidTransactionError("Sender and recipient must differ")
        if not self.signature or not self.sender_public_key:
            raise InvalidTransactionError("Transaction is not signed")
        try:
            derived = address_from_public_key(self.sender_public_key)
        except ValueError:
            raise InvalidTransactionError("Malformed public key")
        if derived != self.sender:
            raise InvalidTransactionError("Public key does not match sender address")
        if not verify_signature(self.sender_public_key, self.payload(), self.signature):
            raise InvalidTransactionError("Invalid signature")

    # --- serialisation -----------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(**data)
