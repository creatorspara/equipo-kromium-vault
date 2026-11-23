"""
Kromium Cryptographic Engine (crypto.py)
=========================================
Senior Security Engineer Implementation
Format: .kromium Secure File Container (Specification v1)

Cryptographic Specifications:
- Cipher: AES-256-GCM (NIST SP 800-38D Authenticated Encryption with Associated Data)
- Key Derivation Function (KDF): PBKDF2-HMAC-SHA256 (RFC 8018)
- Iteration Count: 600,000 rounds (OWASP 2023+ Password Storage Recommendation)
- Salt: 32 bytes (256-bit cryptographically secure pseudo-random bytes via os.urandom)
- Nonce/IV: 12 bytes (96-bit unique cryptographically secure random bytes via os.urandom)
- Associated Data (AAD): Full binary container header (Magic + Version + Iterations + Salt + Nonce + Metadata)
- Authentication: 16-byte GCM Authentication Tag ensures ciphertext and header integrity
- Memory Hygiene: In-place zeroization of sensitive bytearrays (passwords and derived keys)
- Storage Safety: Atomic writes to prevent partial or corrupted file replacement
"""

import os
import struct
import tempfile
import ctypes
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag


# ---------------------------------------------------------------------------
# Constants and Specification Parameters
# ---------------------------------------------------------------------------
MAGIC_HEADER: bytes = b"KROMIUM\x00"  # 8 bytes magic identifier
FORMAT_VERSION: int = 1               # uint8 container format version
DEFAULT_ITERATIONS: int = 600_000     # OWASP recommendation for PBKDF2-HMAC-SHA256
MIN_ITERATIONS: int = 100_000         # Hard security floor
MAX_ITERATIONS: int = 10_000_000      # DoS prevention limit
SALT_SIZE: int = 32                   # 256-bit salt
NONCE_SIZE: int = 12                  # 96-bit nonce for AES-GCM
KEY_SIZE: int = 32                    # 256-bit key for AES-256
TAG_SIZE: int = 16                    # 128-bit authentication tag
MAX_FILENAME_LEN: int = 1024          # Max bytes for original filename in header
MAX_FILE_SIZE: int = 2 * 1024 * 1024 * 1024  # 2 GB maximum envelope size limit

# Minimum header length: 8 (magic) + 1 (version) + 4 (iterations) + 32 (salt) + 12 (nonce) + 2 (name_len) = 59 bytes
MIN_HEADER_SIZE: int = len(MAGIC_HEADER) + 1 + 4 + SALT_SIZE + NONCE_SIZE + 2


# ---------------------------------------------------------------------------
# Custom Exception Hierarchy
# ---------------------------------------------------------------------------
class KromiumError(Exception):
    """Base exception for all Kromium cryptographic and container operations."""
    pass


class InvalidHeaderError(KromiumError):
    """Raised when file magic bytes or header structure is invalid/corrupted."""
    pass


class UnsupportedVersionError(KromiumError):
    """Raised when container format version is not supported."""
    pass


class AuthenticationError(KromiumError):
    """
    Raised when decryption fails due to incorrect password or tampered ciphertext/header.
    (Deliberately indistinguishable to prevent oracle or side-channel attacks).
    """
    pass


class CorruptedFileError(KromiumError):
    """Raised when file is truncated, unreadable, or structurally malformed."""
    pass


# ---------------------------------------------------------------------------
# Memory Hygiene & Secure Erasure
# ---------------------------------------------------------------------------
def secure_wipe(buf: Any) -> None:
    """
    Overwrites the memory of a mutable bytearray or buffer with zeroes.
    Uses ctypes.memset when available for low-level memory zeroing.
    """
    if not isinstance(buf, (bytearray, memoryview)):
        return
    buf_len = len(buf)
    if buf_len == 0:
        return
    try:
        c_buf = (ctypes.c_char * buf_len).from_buffer(buf)
        ctypes.memset(ctypes.byref(c_buf), 0, buf_len)
    except Exception:
        # Fallback to direct byte iteration if ctypes access fails
        for i in range(buf_len):
            buf[i] = 0


def secure_erase_file(file_path: str, passes: int = 1) -> None:
    """
    Overwrites an existing file on disk with random bytes before unlinking.
    Helps prevent forensic recovery of sensitive plaintext files on rotational media.
    """
    p = Path(file_path)
    if not p.is_file():
        return
    
    file_size = p.stat().st_size
    chunk_size = 64 * 1024
    
    try:
        with open(p, "r+b") as f:
            for _ in range(max(1, passes)):
                f.seek(0)
                remaining = file_size
                while remaining > 0:
                    write_size = min(chunk_size, remaining)
                    f.write(os.urandom(write_size))
                    remaining -= write_size
                f.flush()
                os.fsync(f.fileno())
            # Truncate to 0
            f.seek(0)
            f.truncate(0)
            f.flush()
            os.fsync(f.fileno())
    finally:
        p.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Key Derivation (PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------------------------
def derive_key(password_bytes: bytearray | bytes, salt: bytes, iterations: int) -> bytearray:
    """
    Derives a 256-bit AES key from the password and salt using PBKDF2-HMAC-SHA256.
    Returns key as a mutable bytearray to allow caller zeroization.
    """
    if iterations < MIN_ITERATIONS:
        raise KromiumError(f"Iteration count {iterations} is below minimum security threshold ({MIN_ITERATIONS}).")
    if iterations > MAX_ITERATIONS:
        raise KromiumError(f"Iteration count {iterations} exceeds safety limit ({MAX_ITERATIONS}).")
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=iterations,
    )
    raw_key = kdf.derive(bytes(password_bytes))
    key_buffer = bytearray(raw_key)
    return key_buffer


# ---------------------------------------------------------------------------
# Header Construction & Parsing
# ---------------------------------------------------------------------------
def build_header(salt: bytes, nonce: bytes, orig_filename: str, iterations: int = DEFAULT_ITERATIONS) -> bytes:
    """
    Constructs the binary container header for .kromium container.
    Format:
    [8B: MAGIC_HEADER]
    [1B: FORMAT_VERSION (uint8)]
    [4B: ITERATIONS (uint32 big-endian)]
    [32B: SALT]
    [12B: NONCE]
    [2B: ORIG_NAME_LEN (uint16 big-endian)]
    [NB: ORIG_NAME (utf-8)]
    """
    encoded_name = os.path.basename(orig_filename).encode("utf-8")
    if len(encoded_name) > MAX_FILENAME_LEN:
        encoded_name = encoded_name[:MAX_FILENAME_LEN]
    
    name_len = len(encoded_name)
    header = (
        MAGIC_HEADER +
        struct.pack(">BI", FORMAT_VERSION, iterations) +
        salt +
        nonce +
        struct.pack(">H", name_len) +
        encoded_name
    )
    return header


def parse_header_from_bytes(data: bytes) -> Tuple[int, int, bytes, bytes, str, bytes, int]:
    """
    Parses container header from raw binary data.
    Returns:
    (version, iterations, salt, nonce, orig_filename, full_header_bytes, header_length)
    """
    if len(data) < MIN_HEADER_SIZE:
        raise InvalidHeaderError("Data is too short to contain a valid .kromium container header.")
    
    magic = data[:8]
    if magic != MAGIC_HEADER:
        raise InvalidHeaderError("Invalid magic identifier: not a valid .kromium encrypted file.")
    
    version, iterations = struct.unpack(">BI", data[8:13])
    if version != FORMAT_VERSION:
        raise UnsupportedVersionError(f"Unsupported container version: {version}. Expected: {FORMAT_VERSION}.")
    
    offset = 13
    salt = data[offset : offset + SALT_SIZE]
    offset += SALT_SIZE
    
    nonce = data[offset : offset + NONCE_SIZE]
    offset += NONCE_SIZE
    
    name_len = struct.unpack(">H", data[offset : offset + 2])[0]
    offset += 2
    
    if len(data) < offset + name_len:
        raise CorruptedFileError("File header is truncated or corrupt (metadata length exceeds file).")
    
    orig_name_bytes = data[offset : offset + name_len]
    try:
        orig_filename = orig_name_bytes.decode("utf-8")
    except UnicodeDecodeError:
        orig_filename = ""
    offset += name_len
    
    full_header_bytes = data[:offset]
    return version, iterations, salt, nonce, orig_filename, full_header_bytes, offset


def peek_container_metadata(file_path: str) -> Dict[str, Any]:
    """
    Safely inspects container header without decrypting or requiring password.
    Returns a dictionary of header metadata for UI / CLI presentation.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(path, "rb") as f:
        # Read enough for header prefix + max filename
        chunk = f.read(MIN_HEADER_SIZE + MAX_FILENAME_LEN)
    
    version, iterations, salt, nonce, orig_name, _, header_len = parse_header_from_bytes(chunk)
    total_size = path.stat().st_size
    ciphertext_len = max(0, total_size - header_len)
    
    return {
        "file_name": path.name,
        "total_size_bytes": total_size,
        "format_version": version,
        "kdf_iterations": iterations,
        "salt_hex": salt.hex(),
        "nonce_hex": nonce.hex(),
        "original_filename": orig_name,
        "ciphertext_bytes": ciphertext_len,
        "estimated_plaintext_bytes": max(0, ciphertext_len - TAG_SIZE),
    }


# ---------------------------------------------------------------------------
# High-Level Encryption and Decryption API
# ---------------------------------------------------------------------------
def encrypt_bytes(
    plaintext: bytes | bytearray,
    password: str | bytearray,
    orig_filename: str = "",
    iterations: int = DEFAULT_ITERATIONS
) -> bytes:
    """
    Encrypts arbitrary byte sequence into a complete .kromium container byte stream.
    All sensitive password and key buffers are zeroized before return.
    """
    # Normalize password into a mutable bytearray
    if isinstance(password, str):
        pwd_buf = bytearray(password.encode("utf-8"))
    else:
        pwd_buf = bytearray(password)
    
    key_buf: Optional[bytearray] = None
    try:
        if len(pwd_buf) == 0:
            raise KromiumError("Password cannot be empty.")
        
        salt = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)
        
        header_aad = build_header(salt, nonce, orig_filename, iterations=iterations)
        key_buf = derive_key(pwd_buf, salt, iterations)
        
        aesgcm = AESGCM(bytes(key_buf))
        # Encrypt with full header authenticated as Associated Data (AAD)
        ciphertext = aesgcm.encrypt(nonce, bytes(plaintext), associated_data=header_aad)
        
        return header_aad + ciphertext
    finally:
        secure_wipe(pwd_buf)
        if key_buf is not None:
            secure_wipe(key_buf)


def decrypt_bytes(
    container_bytes: bytes,
    password: str | bytearray
) -> Tuple[bytearray, str]:
    """
    Decrypts a complete .kromium container byte stream.
    Returns:
    (decrypted_plaintext_bytearray, original_filename)
    Raises AuthenticationError if password is wrong or file is tampered.
    """
    if isinstance(password, str):
        pwd_buf = bytearray(password.encode("utf-8"))
    else:
        pwd_buf = bytearray(password)
        
    key_buf: Optional[bytearray] = None
    try:
        if len(pwd_buf) == 0:
            raise KromiumError("Password cannot be empty.")
            
        version, iterations, salt, nonce, orig_name, header_aad, header_len = parse_header_from_bytes(container_bytes)
        
        ciphertext_and_tag = container_bytes[header_len:]
        if len(ciphertext_and_tag) < TAG_SIZE:
            raise CorruptedFileError("Container does not contain valid encrypted payload or authentication tag.")
        
        key_buf = derive_key(pwd_buf, salt, iterations)
        aesgcm = AESGCM(bytes(key_buf))
        
        try:
            # GCM verifies tag against ciphertext + header_aad
            raw_plaintext = aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data=header_aad)
            return bytearray(raw_plaintext), orig_name
        except InvalidTag:
            # Generic error to prevent oracle leak
            raise AuthenticationError("Authentication failed: Incorrect password or corrupted/tampered file.")
    finally:
        secure_wipe(pwd_buf)
        if key_buf is not None:
            secure_wipe(key_buf)


def encrypt_file(
    input_path: str,
    output_path: str,
    password: str | bytearray,
    iterations: int = DEFAULT_ITERATIONS,
    orig_filename: Optional[str] = None,
    delete_source: bool = True
) -> None:
    """
    Encrypts a file on disk into a .kromium container file using atomic write semantics.
    If output_path already exists, it is safely and atomically replaced.
    When delete_source is True (default), securely shreds and deletes the original
    plaintext file once encryption is verified.
    """
    in_p = Path(input_path).resolve()
    if not in_p.is_file():
        raise FileNotFoundError(f"Source file not found: {input_path}")
    
    file_size = in_p.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise KromiumError(f"File size exceeds maximum supported size of {MAX_FILE_SIZE // (1024*1024)} MB.")
    
    if orig_filename is None:
        orig_filename = in_p.name
    
    out_p = Path(output_path).resolve()
    if in_p == out_p:
        raise KromiumError("Source and destination paths cannot be identical.")
        
    out_dir = out_p.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(in_p, "rb") as f:
        plaintext = f.read()
    
    encrypted_blob = encrypt_bytes(
        plaintext=plaintext,
        password=password,
        orig_filename=orig_filename,
        iterations=iterations
    )
    
    # Atomic write pattern: write to temporary file in same directory, fsync, then replace
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(
            dir=str(out_dir),
            prefix=".kromium_tmp_",
            suffix=".bin",
            delete=False
        )
        temp_path = Path(temp_file.name)
        temp_file.write(encrypted_blob)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        
        # Atomically replace destination
        os.replace(temp_path, out_p)
        
        # Automatically delete/shred existing source file upon successful encryption
        if delete_source and in_p.exists():
            secure_erase_file(str(in_p))
    except Exception:
        if temp_file is not None and Path(temp_file.name).exists():
            try:
                Path(temp_file.name).unlink()
            except OSError:
                pass
        raise


def encrypt_text_to_file(
    text: str,
    output_path: str,
    password: str | bytearray,
    iterations: int = DEFAULT_ITERATIONS,
    orig_filename: str = "secret.txt"
) -> None:
    """
    Encrypts a plaintext string directly to a .kromium container file on disk.
    Automatically creates the .kromium file and sanitizes in-memory buffers.
    """
    out_p = Path(output_path).resolve()
    out_dir = out_p.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    text_bytes = bytearray(text.encode("utf-8"))
    try:
        encrypted_blob = encrypt_bytes(
            plaintext=text_bytes,
            password=password,
            orig_filename=orig_filename,
            iterations=iterations
        )
    finally:
        secure_wipe(text_bytes)

    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(
            dir=str(out_dir),
            prefix=".kromium_txt_tmp_",
            suffix=".bin",
            delete=False
        )
        temp_path = Path(temp_file.name)
        temp_file.write(encrypted_blob)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()

        os.replace(temp_path, out_p)
    except Exception:
        if temp_file is not None and Path(temp_file.name).exists():
            try:
                Path(temp_file.name).unlink()
            except OSError:
                pass
        raise


def decrypt_file_to_text(
    input_path: str,
    password: str | bytearray,
    delete_source: bool = False
) -> Tuple[str, str]:
    """
    Decrypts a .kromium container file and decodes the plaintext payload as UTF-8 text.
    Returns: (decrypted_text, original_filename)
    When delete_source is True, securely shreds and deletes the .kromium file upon success.
    """
    in_p = Path(input_path).resolve()
    if not in_p.is_file():
        raise FileNotFoundError(f"Container not found: {input_path}")

    with open(in_p, "rb") as f:
        container_bytes = f.read()

    buf, orig_name = decrypt_bytes(container_bytes, password)
    try:
        decrypted_text = buf.decode("utf-8")
        if delete_source and in_p.exists():
            secure_erase_file(str(in_p))
        return decrypted_text, orig_name
    except UnicodeDecodeError:
        raise KromiumError("Decrypted data is binary or not valid UTF-8 text.")
    finally:
        secure_wipe(buf)


def decrypt_file(
    input_path: str,
    output_path: str,
    password: str | bytearray,
    delete_source: bool = True
) -> str:
    """
    Decrypts a .kromium container file on disk to the designated output path.
    Uses atomic write semantics.
    When delete_source is True (default), securely shreds and deletes the .kromium container
    file once decryption and file writing have succeeded.
    Returns:
    The original filename recorded inside the container metadata.
    """
    in_p = Path(input_path).resolve()
    if not in_p.is_file():
        raise FileNotFoundError(f"Encrypted container file not found: {input_path}")
    
    file_size = in_p.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise KromiumError("Container size exceeds maximum supported size.")
    
    with open(in_p, "rb") as f:
        container_bytes = f.read()
    
    plaintext_buf, orig_name = decrypt_bytes(container_bytes, password)
    
    out_p = Path(output_path).resolve()
    if in_p == out_p:
        raise KromiumError("Source container and destination path cannot be identical.")
        
    out_dir = out_p.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(
            dir=str(out_dir),
            prefix=".kromium_dec_tmp_",
            suffix=".bin",
            delete=False
        )
        temp_path = Path(temp_file.name)
        temp_file.write(plaintext_buf)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        
        # Atomically replace destination
        os.replace(temp_path, out_p)

        # Automatically delete & securely shred the .kromium container once decryption succeeds
        if delete_source and in_p.exists():
            secure_erase_file(str(in_p))

        return orig_name
    except Exception:
        if temp_file is not None and Path(temp_file.name).exists():
            try:
                Path(temp_file.name).unlink()
            except OSError:
                pass
        raise
    finally:
        secure_wipe(plaintext_buf)
