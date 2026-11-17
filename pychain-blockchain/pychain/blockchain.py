"""The chain itself: transaction pool, mining, balances and validation."""
import time

from . import config
from .block import Block
from .exceptions import InvalidTransactionError
from .logger import get_logger
from .transaction import Transaction

log = get_logger("blockchain")
EPSILON = 1e-9


class Blockchain:
    def __init__(
        self,
        difficulty: int | None = None,
        mining_reward: float | None = None,
    ):
        # Read config at call time so values can be overridden (e.g. in tests).
        self.difficulty = config.DIFFICULTY if difficulty is None else difficulty
        self.mining_reward = config.MINING_REWARD if mining_reward is None else mining_reward
        self.chain: list[Block] = [self._genesis_block()]
        self.pending: list[Transaction] = []
        log.debug("Blockchain initialised (difficulty=%d)", self.difficulty)

    @staticmethod
    def _genesis_block() -> Block:
        """Deterministic first block so every node starts from the same state."""
        block = Block(
            index=0,
            transactions=[],
            previous_hash=config.GENESIS_PREVIOUS_HASH,
            timestamp=0.0,
        )
        block.hash = block.compute_hash()
        return block

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    # --- balances ----------------------------------------------------------
    def get_balance(self, address: str, include_pending: bool = False) -> float:
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == address:
                    balance += tx.amount
                if tx.sender == address:
                    balance -= tx.amount
        if include_pending:
            for tx in self.pending:
                if tx.sender == address:
                    balance -= tx.amount
        return round(balance, 8)

    # --- transactions ------------------------------------------------------
    def add_transaction(self, tx: Transaction) -> None:
        """Validate a transaction and place it in the pending pool."""
        if tx.is_coinbase:
            raise InvalidTransactionError("Coinbase transactions cannot be submitted")
        tx.validate()
        if any(p.tx_id == tx.tx_id for p in self.pending):
            raise InvalidTransactionError("Duplicate transaction")
        available = self.get_balance(tx.sender, include_pending=True)
        if available + EPSILON < tx.amount:
            raise InvalidTransactionError(
                f"Insufficient funds: available {available}, needed {tx.amount}"
            )
        self.pending.append(tx)
        log.info(
            "Transaction accepted %s: %s -> %s amount=%s",
            tx.tx_id[:12], tx.sender[:10], tx.recipient[:10], tx.amount,
        )

    # --- mining ------------------------------------------------------------
    def mine_pending(self, miner_address: str) -> Block:
        """Bundle pending transactions (plus the reward) into a mined block."""
        reward = Transaction(
            sender=config.COINBASE_SENDER,
            recipient=miner_address,
            amount=self.mining_reward,
        )
        block = Block(
            index=len(self.chain),
            transactions=[reward, *self.pending],
            previous_hash=self.last_block.hash,
        )
        log.info(
            "Mining block %d with %d transaction(s)...", block.index, len(block.transactions)
        )
        started = time.perf_counter()
        block.mine(self.difficulty)
        elapsed = time.perf_counter() - started
        self.chain.append(block)
        self.pending = []
        log.info(
            "Block %d mined in %.2fs nonce=%d hash=%s",
            block.index, elapsed, block.nonce, block.hash,
        )
        return block

    # --- validation --------------------------------------------------------
    def is_valid(self) -> tuple[bool, str]:
        """Full audit of the chain. Returns ``(ok, reason)``."""
        if not self.chain or self.chain[0].hash != self._genesis_block().hash:
            return False, "Genesis block is missing or altered"

        target = "0" * self.difficulty
        balances: dict[str, float] = {}

        for i, block in enumerate(self.chain):
            if block.index != i:
                return False, f"Block {i}: wrong index"
            if block.hash != block.compute_hash():
                return False, f"Block {i}: hash does not match contents"
            if i == 0:
                continue
            if block.previous_hash != self.chain[i - 1].hash:
                return False, f"Block {i}: broken link to previous block"
            if not block.hash.startswith(target):
                return False, f"Block {i}: proof of work is insufficient"

            txs = block.transactions
            if not txs or not txs[0].is_coinbase:
                return False, f"Block {i}: missing coinbase transaction"
            if txs[0].amount != self.mining_reward:
                return False, f"Block {i}: wrong mining reward"
            if any(t.is_coinbase for t in txs[1:]):
                return False, f"Block {i}: more than one coinbase transaction"

            for tx in txs:
                try:
                    tx.validate()
                except InvalidTransactionError as exc:
                    return False, f"Block {i}: {exc}"
                if not tx.is_coinbase:
                    balances[tx.sender] = balances.get(tx.sender, 0.0) - tx.amount
                    if balances[tx.sender] < -EPSILON:
                        return False, f"Block {i}: {tx.sender[:10]} overspent"
                balances[tx.recipient] = balances.get(tx.recipient, 0.0) + tx.amount

        return True, "Chain is valid"

    # --- serialisation -----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "difficulty": self.difficulty,
            "mining_reward": self.mining_reward,
            "chain": [b.to_dict() for b in self.chain],
            "pending": [t.to_dict() for t in self.pending],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Blockchain":
        bc = cls(data["difficulty"], data["mining_reward"])
        bc.chain = [Block.from_dict(b) for b in data["chain"]]
        bc.pending = [Transaction.from_dict(t) for t in data["pending"]]
        return bc
