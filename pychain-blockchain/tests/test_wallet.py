import tempfile
import unittest
from pathlib import Path

from pychain.wallet import Wallet, verify_signature


class WalletTests(unittest.TestCase):
    def test_sign_and_verify(self):
        w = Wallet()
        sig = w.sign("hello")
        self.assertTrue(verify_signature(w.public_key_hex, "hello", sig))

    def test_tampered_message_fails(self):
        w = Wallet()
        sig = w.sign("hello")
        self.assertFalse(verify_signature(w.public_key_hex, "hellO", sig))

    def test_wrong_key_fails(self):
        sig = Wallet().sign("hello")
        self.assertFalse(verify_signature(Wallet().public_key_hex, "hello", sig))

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "w.pem"
            w = Wallet()
            w.save(path)
            self.assertEqual(Wallet.load(path).address, w.address)


if __name__ == "__main__":
    unittest.main()
