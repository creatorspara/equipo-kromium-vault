"""
Unit and Security Test Suite for Kromium Cryptographic Engine
"""

import os
import unittest
import tempfile
from pathlib import Path

from crypto import (
    encrypt_bytes,
    decrypt_bytes,
    encrypt_file,
    encrypt_text_to_file,
    decrypt_file,
    decrypt_file_to_text,
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
    MIN_ITERATIONS
)


class TestKromiumCrypto(unittest.TestCase):
    def setUp(self):
        self.test_password = "P@ssw0rd!#SecureCrypto2026_Test"
        self.test_data = b"CLASSIFIED_CREDENTIALS_AND_KEYS_DATABASE_RECORD_XYZ1234567890"

    def test_roundtrip_bytes(self):
        """Test encryption and decryption roundtrip for in-memory bytes."""
        encrypted = encrypt_bytes(
            self.test_data,
            self.test_password,
            orig_filename="vault.json",
            iterations=MIN_ITERATIONS
        )
        self.assertTrue(encrypted.startswith(MAGIC_HEADER))
        
        decrypted, orig_name = decrypt_bytes(encrypted, self.test_password)
        self.assertEqual(bytes(decrypted), self.test_data)
        self.assertEqual(orig_name, "vault.json")

    def test_encrypt_text_to_file_and_decrypt_to_text(self):
        """Test direct text encryption automatically creates .kromium container and decrypts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out_file = Path(temp_dir) / "direct_note.kromium"
            secret_text = "Master Password = CorrectHorseBatteryStaple!987\nAPI_KEY=live_tok_998877"
            
            # Encrypt text directly to .kromium file
            encrypt_text_to_file(secret_text, str(out_file), self.test_password, iterations=MIN_ITERATIONS)
            self.assertTrue(out_file.is_file())
            
            # Verify metadata
            meta = peek_container_metadata(str(out_file))
            self.assertEqual(meta["format_version"], 1)
            
            # Decrypt directly to string
            recovered_text, _ = decrypt_file_to_text(str(out_file), self.test_password)
            self.assertEqual(recovered_text, secret_text)

    def test_automatic_deletion_of_existing_file_on_encryption(self):
        """Test that encrypt_file automatically deletes and shreds the original source file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_file = Path(temp_dir) / "cleartext_passwords.txt"
            container_file = Path(temp_dir) / "passwords.kromium"
            restored_file = Path(temp_dir) / "recovered_passwords.txt"
            
            source_file.write_text("BANK_PASS=123456", encoding="utf-8")
            self.assertTrue(source_file.is_file())
            
            # Encrypt with default delete_source=True
            encrypt_file(str(source_file), str(container_file), self.test_password, iterations=MIN_ITERATIONS)
            
            # Container must exist
            self.assertTrue(container_file.is_file())
            # Source file MUST be automatically deleted
            self.assertFalse(source_file.exists())
            
            # Verify decryption restores data and automatically deletes the .kromium file
            orig = decrypt_file(str(container_file), str(restored_file), self.test_password)
            self.assertEqual(restored_file.read_text(encoding="utf-8"), "BANK_PASS=123456")
            self.assertEqual(orig, "cleartext_passwords.txt")
            # Container file MUST be automatically deleted upon decryption
            self.assertFalse(container_file.exists())

    def test_automatic_deletion_of_kromium_file_on_decryption(self):
        """Test that decrypt_file automatically deletes the .kromium file once decrypted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plain_file = Path(temp_dir) / "secret.txt"
            plain_file.write_text("Classified Vault Key = 998877", encoding="utf-8")
            krom_file = Path(temp_dir) / "secret.txt.kromium"
            out_file = Path(temp_dir) / "restored_secret.txt"

            encrypt_file(str(plain_file), str(krom_file), self.test_password, iterations=MIN_ITERATIONS, delete_source=False)
            self.assertTrue(krom_file.exists())

            # Decrypt with default delete_source=True
            decrypt_file(str(krom_file), str(out_file), self.test_password)

            self.assertTrue(out_file.exists())
            self.assertEqual(out_file.read_text(encoding="utf-8"), "Classified Vault Key = 998877")
            # .kromium file must be shredded and deleted
            self.assertFalse(krom_file.exists())

    def test_failed_decryption_preserves_kromium_file(self):
        """Test that wrong password does NOT delete the .kromium container file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plain_file = Path(temp_dir) / "secret.txt"
            plain_file.write_text("Keep me safe", encoding="utf-8")
            krom_file = Path(temp_dir) / "secret.txt.kromium"
            out_file = Path(temp_dir) / "restored.txt"

            encrypt_file(str(plain_file), str(krom_file), self.test_password, iterations=MIN_ITERATIONS, delete_source=False)
            self.assertTrue(krom_file.exists())

            with self.assertRaises(AuthenticationError):
                decrypt_file(str(krom_file), str(out_file), "WrongMasterKey!123")

            # .kromium file MUST STILL EXIST because password was wrong!
            self.assertTrue(krom_file.exists())
            self.assertFalse(out_file.exists())

    def test_preserve_kromium_file_when_delete_source_false(self):
        """Test that .kromium file is preserved when delete_source=False is explicitly passed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plain_file = Path(temp_dir) / "data.txt"
            plain_file.write_text("Preserve container test", encoding="utf-8")
            krom_file = Path(temp_dir) / "data.txt.kromium"
            out_file = Path(temp_dir) / "data_out.txt"

            encrypt_file(str(plain_file), str(krom_file), self.test_password, iterations=MIN_ITERATIONS, delete_source=False)
            decrypt_file(str(krom_file), str(out_file), self.test_password, delete_source=False)

            self.assertTrue(out_file.exists())
            self.assertTrue(krom_file.exists())

    def test_preserve_source_when_delete_source_false(self):
        """Test that source file is preserved when delete_source=False is explicitly specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_file = Path(temp_dir) / "keep_me.txt"
            container_file = Path(temp_dir) / "keep_me.txt.kromium"
            
            source_file.write_text("Preserve this file", encoding="utf-8")
            encrypt_file(str(source_file), str(container_file), self.test_password, iterations=MIN_ITERATIONS, delete_source=False)
            
            self.assertTrue(container_file.is_file())
            self.assertTrue(source_file.is_file())

    def test_empty_plaintext(self):
        """Test encryption and decryption of an empty payload."""
        encrypted = encrypt_bytes(b"", self.test_password, orig_filename="empty.txt", iterations=MIN_ITERATIONS)
        decrypted, orig_name = decrypt_bytes(encrypted, self.test_password)
        self.assertEqual(bytes(decrypted), b"")
        self.assertEqual(orig_name, "empty.txt")

    def test_wrong_password_raises_authentication_error(self):
        """Test that incorrect password fails authentication with AuthenticationError."""
        encrypted = encrypt_bytes(self.test_data, self.test_password, iterations=MIN_ITERATIONS)
        with self.assertRaises(AuthenticationError):
            decrypt_bytes(encrypted, "WrongPassword!987654321")

    def test_tampered_ciphertext_fails(self):
        """Test that tampering with any byte of ciphertext causes AEAD tag verification failure."""
        encrypted = bytearray(encrypt_bytes(self.test_data, self.test_password, iterations=MIN_ITERATIONS))
        
        # Tamper with authentication tag
        encrypted[-1] ^= 0x01
        with self.assertRaises(AuthenticationError):
            decrypt_bytes(bytes(encrypted), self.test_password)

        # Tamper with ciphertext
        encrypted = bytearray(encrypt_bytes(self.test_data, self.test_password, iterations=MIN_ITERATIONS))
        encrypted[-20] ^= 0x55
        with self.assertRaises(AuthenticationError):
            decrypt_bytes(bytes(encrypted), self.test_password)

    def test_tampered_header_fails_or_rejects(self):
        """Test that tampering with salt, nonce, or metadata fails AEAD verification or raises InvalidHeaderError."""
        encrypted = bytearray(encrypt_bytes(self.test_data, self.test_password, orig_filename="passwords.kdbx", iterations=MIN_ITERATIONS))
        
        # Tamper with magic header
        corrupt_magic = bytearray(encrypted)
        corrupt_magic[0] ^= 0xFF
        with self.assertRaises(InvalidHeaderError):
            decrypt_bytes(bytes(corrupt_magic), self.test_password)
        
        # Tamper with Salt
        corrupt_salt = bytearray(encrypted)
        corrupt_salt[15] ^= 0x01
        with self.assertRaises(AuthenticationError):
            decrypt_bytes(bytes(corrupt_salt), self.test_password)

        # Tamper with Nonce
        corrupt_nonce = bytearray(encrypted)
        corrupt_nonce[46] ^= 0x01
        with self.assertRaises(AuthenticationError):
            decrypt_bytes(bytes(corrupt_nonce), self.test_password)

    def test_unique_salts_and_nonces_per_run(self):
        """Test that encrypting the same plaintext twice produces distinct salts, nonces, and ciphertexts."""
        enc1 = encrypt_bytes(self.test_data, self.test_password, iterations=MIN_ITERATIONS)
        enc2 = encrypt_bytes(self.test_data, self.test_password, iterations=MIN_ITERATIONS)
        self.assertNotEqual(enc1, enc2)
        self.assertNotEqual(enc1[13:45], enc2[13:45])
        self.assertNotEqual(enc1[45:57], enc2[45:57])

    def test_secure_wipe_memory(self):
        """Test that secure_wipe resets all buffer bytes to 0x00."""
        buf = bytearray(b"HighlySecretPasswordMemory123")
        self.assertNotEqual(buf, bytearray(len(buf)))
        secure_wipe(buf)
        self.assertEqual(buf, bytearray(len(buf)))

    def test_secure_erase_file(self):
        """Test file shredding overwrites and unlinks file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            secret_file = Path(temp_dir) / "shred_me.txt"
            secret_file.write_bytes(b"Top secret content to shred immediately")
            self.assertTrue(secret_file.is_file())
            
            secure_erase_file(str(secret_file), passes=2)
            self.assertFalse(secret_file.exists())


if __name__ == "__main__":
    unittest.main()
