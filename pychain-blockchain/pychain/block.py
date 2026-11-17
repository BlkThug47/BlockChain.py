"""A block: a batch of transactions linked to its predecessor by hash."""
import hashlib
import json
import time
from dataclasses import dataclass, field

from .transaction import Transaction


def merkle_root(tx_ids: list[str]) -> str:
    """Compute the Merkle root of a list of transaction ids."""
    if not tx_ids:
        return hashlib.sha256(b"").hexdigest()
    level = list(tx_ids)
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])  # duplicate the last node on odd levels
        level = [
            hashlib.sha256((level[i] + level[i + 1]).encode()).hexdigest()
            for i in range(0, len(level), 2)
        ]
    return level[0]


@dataclass
class Block:
    index: int
    transactions: list[Transaction]
    previous_hash: str
    timestamp: float = field(default_factory=time.time)
    nonce: int = 0
    hash: str = ""

    @property
    def merkle_root(self) -> str:
        return merkle_root([tx.tx_id for tx in self.transactions])

    def compute_hash(self) -> str:
        header = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "merkle_root": self.merkle_root,
                "previous_hash": self.previous_hash,
                "nonce": self.nonce,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(header.encode()).hexdigest()

    def mine(self, difficulty: int) -> None:
        """Proof of work: increment the nonce until the hash has N leading zeros."""
        target = "0" * difficulty
        self.nonce = 0
        self.hash = self.compute_hash()
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.compute_hash()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            transactions=[Transaction.from_dict(t) for t in data["transactions"]],
            previous_hash=data["previous_hash"],
            nonce=data["nonce"],
            hash=data["hash"],
        )
