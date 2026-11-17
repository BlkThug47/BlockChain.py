import unittest

from pychain.exceptions import InvalidTransactionError
from pychain.transaction import Transaction
from pychain.wallet import Wallet

from .helpers import make_chain, signed_tx


class BlockchainTests(unittest.TestCase):
    def setUp(self):
        self.chain = make_chain()
        self.alice, self.bob = Wallet(), Wallet()

    def test_genesis_block_exists(self):
        self.assertEqual(len(self.chain.chain), 1)
        self.assertTrue(self.chain.is_valid()[0])

    def test_mining_rewards_miner_and_meets_difficulty(self):
        block = self.chain.mine_pending(self.alice.address)
        self.assertTrue(block.hash.startswith("0" * self.chain.difficulty))
        self.assertEqual(self.chain.get_balance(self.alice.address), self.chain.mining_reward)

    def test_transfer_updates_balances(self):
        self.chain.mine_pending(self.alice.address)
        self.chain.add_transaction(signed_tx(self.alice, self.bob.address, 10))
        self.chain.mine_pending(self.bob.address)
        self.assertEqual(self.chain.get_balance(self.bob.address), 10 + self.chain.mining_reward)
        self.assertEqual(self.chain.get_balance(self.alice.address), self.chain.mining_reward - 10)

    def test_overspend_rejected(self):
        with self.assertRaises(InvalidTransactionError):
            self.chain.add_transaction(signed_tx(self.alice, self.bob.address, 1))

    def test_pending_spend_counts_against_balance(self):
        self.chain.mine_pending(self.alice.address)
        self.chain.add_transaction(signed_tx(self.alice, self.bob.address, 40))
        with self.assertRaises(InvalidTransactionError):
            self.chain.add_transaction(signed_tx(self.alice, self.bob.address, 40))

    def test_unsigned_and_forged_transactions_rejected(self):
        self.chain.mine_pending(self.alice.address)
        unsigned = Transaction(self.alice.address, self.bob.address, 5)
        with self.assertRaises(InvalidTransactionError):
            self.chain.add_transaction(unsigned)
        forged = signed_tx(self.alice, self.bob.address, 5)
        forged.amount = 500  # tamper after signing
        with self.assertRaises(InvalidTransactionError):
            self.chain.add_transaction(forged)

    def test_cannot_sign_for_someone_else(self):
        tx = Transaction(self.alice.address, self.bob.address, 5)
        with self.assertRaises(InvalidTransactionError):
            tx.sign(self.bob)

    def test_tampering_with_history_is_detected(self):
        self.chain.mine_pending(self.alice.address)
        self.chain.add_transaction(signed_tx(self.alice, self.bob.address, 10))
        self.chain.mine_pending(self.alice.address)
        self.chain.chain[2].transactions[1].amount = 1
        ok, reason = self.chain.is_valid()
        self.assertFalse(ok)
        self.assertIn("Block 2", reason)

    def test_broken_link_is_detected(self):
        self.chain.mine_pending(self.alice.address)
        self.chain.mine_pending(self.alice.address)
        self.chain.chain[1].previous_hash = "f" * 64
        self.assertFalse(self.chain.is_valid()[0])

    def test_inflated_reward_is_detected(self):
        self.chain.mine_pending(self.alice.address)
        block = self.chain.chain[1]
        block.transactions[0].amount = 1_000_000
        block.mine(self.chain.difficulty)  # re-mined, but reward is still wrong
        self.assertFalse(self.chain.is_valid()[0])


if __name__ == "__main__":
    unittest.main()
