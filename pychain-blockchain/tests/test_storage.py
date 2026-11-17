import json
import tempfile
import unittest
from pathlib import Path

from pychain import storage
from pychain.exceptions import InvalidChainError, StorageError
from pychain.wallet import Wallet

from .helpers import make_chain, signed_tx


class StorageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "chain.json"
        self.addCleanup(self._tmp.cleanup)

    def test_roundtrip_preserves_chain_and_pending(self):
        alice, bob = Wallet(), Wallet()
        chain = make_chain()
        chain.mine_pending(alice.address)
        chain.add_transaction(signed_tx(alice, bob.address, 7))
        storage.save_chain(chain, self.path)

        loaded = storage.load_chain(self.path)
        self.assertEqual(len(loaded.chain), 2)
        self.assertEqual(len(loaded.pending), 1)
        self.assertEqual(loaded.get_balance(alice.address), chain.get_balance(alice.address))

    def test_missing_file_returns_new_chain(self):
        self.assertEqual(len(storage.load_chain(self.path).chain), 1)

    def test_tampered_file_is_rejected(self):
        alice = Wallet()
        chain = make_chain()
        chain.mine_pending(alice.address)
        storage.save_chain(chain, self.path)
        data = json.loads(self.path.read_text())
        data["chain"][1]["transactions"][0]["amount"] = 9999
        self.path.write_text(json.dumps(data))
        with self.assertRaises(InvalidChainError):
            storage.load_chain(self.path)

    def test_corrupt_json_raises_storage_error(self):
        self.path.write_text("{not json")
        with self.assertRaises(StorageError):
            storage.load_chain(self.path)

    def test_backup_created_on_second_save(self):
        chain = make_chain()
        storage.save_chain(chain, self.path)
        storage.save_chain(chain, self.path)
        self.assertTrue(self.path.with_suffix(".bak").exists())


if __name__ == "__main__":
    unittest.main()
