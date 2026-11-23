"""
End-to-End Cryptographic & Security Verification Suite
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crypto import (
    encrypt_file,
    decrypt_file,
    peek_container_metadata,
    secure_wipe,
    secure_erase_file,
    AuthenticationError,
    InvalidHeaderError,
    UnsupportedVersionError,
    CorruptedFileError,
    KromiumError,
    MAGIC_HEADER,
    DEFAULT_ITERATIONS,
    MIN_ITERATIONS,
)


class TestKromiumSecurityE2E(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)
        self.test_password = "Kromium#Vault@MasterPassword9921!"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_e2e_full_file_encryption_decryption(self):
        """Verify full round-trip file encryption and restoration."""
        plain_path = self.dir_path / "financial_passwords.txt"
        enc_path = self.dir_path / "financial_passwords.txt.kromium"
        dec_path = self.dir_path / "restored_passwords.txt"

        original_data = (
            b"Service: PrimaryBank\nUsername: security_admin\nPassword: 98*&(sdf9872!#\n"
            b"PIN: 4920\nRecoveryKeys: [abc-123, def-456, ghi-789]"
        )
        plain_path.write_bytes(original_data)

        # Encrypt with full production iterations (automatically deletes source file)
        encrypt_file(str(plain_path), str(enc_path), self.test_password, iterations=100_000)

        self.assertTrue(enc_path.exists())
        self.assertFalse(plain_path.exists())  # Source file must be automatically deleted
        self.assertGreater(enc_path.stat().st_size, len(original_data))

        # Inspect metadata without decrypting
        meta = peek_container_metadata(str(enc_path))
        self.assertEqual(meta["format_version"], 1)
        self.assertEqual(meta["kdf_iterations"], 100_000)
        self.assertEqual(meta["original_filename"], "financial_passwords.txt")
        self.assertEqual(len(meta["salt_hex"]), 64)  # 32 bytes = 64 hex chars
        self.assertEqual(len(meta["nonce_hex"]), 24) # 12 bytes = 24 hex chars

        # Decrypt (automatically deletes .kromium container)
        orig_name = decrypt_file(str(enc_path), str(dec_path), self.test_password)
        self.assertEqual(orig_name, "financial_passwords.txt")
        self.assertEqual(dec_path.read_bytes(), original_data)
        self.assertFalse(enc_path.exists())  # .kromium container must be automatically deleted

    def test_unicode_filename_preservation(self):
        """Verify files with Unicode characters in names preserve metadata."""
        plain_path = self.dir_path / "🔒_mots_de_passe_trésor_2026.json"
        enc_path = self.dir_path / "secure_vault.kromium"
        dec_path = self.dir_path / "recovered.json"

        data = b'{"api_token": "secret_vault_token_value_4455"}'
        plain_path.write_bytes(data)

        encrypt_file(str(plain_path), str(enc_path), self.test_password, iterations=100_000)
        meta = peek_container_metadata(str(enc_path))
        self.assertEqual(meta["original_filename"], "🔒_mots_de_passe_trésor_2026.json")

        orig_name = decrypt_file(str(enc_path), str(dec_path), self.test_password)
        self.assertEqual(orig_name, "🔒_mots_de_passe_trésor_2026.json")
        self.assertEqual(dec_path.read_bytes(), data)

    def test_rejection_of_truncated_file(self):
        """Truncated files should be cleanly rejected with InvalidHeaderError or CorruptedFileError."""
        bad_path = self.dir_path / "truncated.kromium"
        bad_path.write_bytes(b"KROMIUM\x00\x01\x00")  # Incomplete header

        with self.assertRaises(InvalidHeaderError):
            peek_container_metadata(str(bad_path))

        with self.assertRaises(InvalidHeaderError):
            decrypt_file(str(bad_path), str(self.dir_path / "out.txt"), self.test_password)

    def test_rejection_of_tampered_metadata(self):
        """Tampering with iteration count in header causes AEAD tag failure."""
        plain_path = self.dir_path / "secret.txt"
        enc_path = self.dir_path / "secret.txt.kromium"
        dec_path = self.dir_path / "out.txt"

        plain_path.write_bytes(b"Top secret")
        encrypt_file(str(plain_path), str(enc_path), self.test_password, iterations=100_000)

        # Modify iteration count in header (bytes 9..12)
        content = bytearray(enc_path.read_bytes())
        content[10] ^= 0xFF
        enc_path.write_bytes(content)

        with self.assertRaises((AuthenticationError, KromiumError)):
            decrypt_file(str(enc_path), str(dec_path), self.test_password)

    def test_no_temp_leak_on_failure(self):
        """Failed decryption should not leave temp files behind."""
        plain_path = self.dir_path / "secret2.txt"
        enc_path = self.dir_path / "secret2.txt.kromium"
        dec_path = self.dir_path / "out2.txt"

        plain_path.write_bytes(b"Sensitive data")
        encrypt_file(str(plain_path), str(enc_path), self.test_password, iterations=100_000)

        # Wrong password
        try:
            decrypt_file(str(enc_path), str(dec_path), "IncorrectPassword123!")
        except AuthenticationError:
            pass

        self.assertFalse(dec_path.exists())
        # Ensure no leftover .kromium_dec_tmp_* files exist
        temp_files = list(self.dir_path.glob(".kromium_dec_tmp_*"))
        self.assertEqual(len(temp_files), 0)


if __name__ == "__main__":
    unittest.main()
