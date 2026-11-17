"""ECDSA (secp256k1) wallets, signing and signature verification."""
import hashlib
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from .logger import get_logger

log = get_logger("wallet")


def address_from_public_key(public_key_hex: str) -> str:
    """An address is the first 40 hex chars of SHA-256(public key)."""
    return hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:40]


def verify_signature(public_key_hex: str, message: str, signature_hex: str) -> bool:
    """Return True if ``signature_hex`` is a valid signature of ``message``."""
    try:
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256K1(), bytes.fromhex(public_key_hex)
        )
        public_key.verify(
            bytes.fromhex(signature_hex), message.encode(), ec.ECDSA(hashes.SHA256())
        )
        return True
    except (InvalidSignature, ValueError):
        return False


class Wallet:
    """Holds a private key and derives the public key and address from it."""

    def __init__(self, private_key: ec.EllipticCurvePrivateKey | None = None):
        self._private_key = private_key or ec.generate_private_key(ec.SECP256K1())

    @property
    def public_key_hex(self) -> str:
        return (
            self._private_key.public_key()
            .public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint,
            )
            .hex()
        )

    @property
    def address(self) -> str:
        return address_from_public_key(self.public_key_hex)

    def sign(self, message: str) -> str:
        signature = self._private_key.sign(message.encode(), ec.ECDSA(hashes.SHA256()))
        return signature.hex()

    # --- persistence -------------------------------------------------------
    def save(self, path: Path) -> None:
        """Write the private key as PEM (unencrypted - fine for a demo project)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        pem = self._private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        path.write_bytes(pem)
        path.chmod(0o600)
        log.info("Wallet saved: %s (address=%s)", path.name, self.address)

    @classmethod
    def load(cls, path: Path) -> "Wallet":
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        return cls(key)
