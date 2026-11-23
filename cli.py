"""
Kromium Vault - Interactive & Terminal CLI (cli.py)
===================================================
Senior Security Engineer Implementation
Provides an interactive command-line workflow that prompts the user
to:
1. Enter sensitive text directly to automatically create a .kromium container file.
2. Select a file via a native file dialog (or path) and automatically delete the existing file upon encryption.
3. Decrypt existing .kromium container files back to disk or preview directly.
"""

import os
import sys
import getpass
import argparse
from pathlib import Path
from typing import Optional

from crypto import (
    encrypt_file,
    encrypt_text_to_file,
    decrypt_file,
    decrypt_file_to_text,
    peek_container_metadata,
    secure_erase_file,
    secure_wipe,
    AuthenticationError,
    InvalidHeaderError,
    UnsupportedVersionError,
    CorruptedFileError,
    KromiumError,
    DEFAULT_ITERATIONS,
)


def select_file_via_dialog(prompt_title: str = "Select File for Kromium Vault") -> Optional[str]:
    """
    Opens a native OS file dialog box to allow user to graphically choose a file.
    Returns chosen path, or None if cancelled.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        
        chosen = filedialog.askopenfilename(
            title=prompt_title,
            filetypes=[
                ("Kromium Vault Files (*.kromium)", "*.kromium"),
                ("All Files (*.*)", "*.*")
            ]
        )
        root.destroy()
        return chosen if chosen else None
    except Exception as e:
        print(f"[!] Graphical file dialog unavailable ({e}). Falling back to manual entry.")
        return None


def print_banner():
    """Prints the security header."""
    print("=" * 68)
    print("  🛡️  KROMIUM SECURITY VAULT - Cryptographic Container Tool")
    print("  • Direct Text Encryption: Automatically generates .kromium container")
    print("  • File Encryption: Automatically shreds & deletes original file")
    print("  • Cipher: AES-256-GCM AEAD  •  KDF: PBKDF2-HMAC-SHA256 (600,000 Rounds)")
    print("=" * 68)


def interactive_workflow():
    """
    Runs the step-by-step interactive workflow prompting the user
    for text entry or file selection, mode, and credentials.
    """
    print_banner()
    print("\n[+] Step 1: Select Operation")
    print("    1. Enter sensitive text directly (Automatically creates .kromium file)")
    print("    2. Encrypt an existing file (Automatically deletes original when done)")
    print("    3. Decrypt a .kromium container file")
    
    choice = input("\nSelect an option [1/2/3, default 1]: ").strip()
    if choice not in ("1", "2", "3"):
        choice = "1"

    if choice == "1":
        # Direct text entry workflow
        print("\n[+] Enter the sensitive text, passwords, or credentials to encrypt.")
        print("    (Type your text below and press Enter):")
        text_content = input("Secret text: ").strip()
        if not text_content:
            print("[!] Error: Text content cannot be empty.")
            sys.exit(1)

        default_dest = str(Path.cwd() / "vault_secret.kromium")
        dest_input = input(f"\nEnter destination .kromium path [Press Enter for '{default_dest}']: ").strip().strip('"').strip("'")
        destination = dest_input if dest_input else default_dest
        if not destination.lower().endswith(".kromium"):
            destination += ".kromium"

        print("\n[+] Step 2: Master Password")
        pwd_raw = getpass.getpass("Enter Master Password: ")
        if not pwd_raw:
            print("[!] Error: Password cannot be empty.")
            sys.exit(1)
        confirm_pwd = getpass.getpass("Confirm Master Password: ")
        if pwd_raw != confirm_pwd:
            print("[!] Error: Passwords do not match.")
            sys.exit(1)

        pwd_bytes = bytearray(pwd_raw.encode("utf-8"))
        del pwd_raw

        print("\n[*] Processing encryption (600,000 PBKDF2 iterations)...")
        try:
            encrypt_text_to_file(text_content, destination, pwd_bytes, iterations=DEFAULT_ITERATIONS)
            print(f"\n[✔] SUCCESS: Automatically created .kromium file from text at:")
            print(f"    {destination}")
        except Exception as e:
            print(f"\n[!] ERROR: Failed to encrypt text ({e})")
            sys.exit(1)
        finally:
            secure_wipe(pwd_bytes)
            print("[*] Memory sanitized: Master key and password buffers zeroized.")
        return

    elif choice == "2":
        # Encrypt file on disk & automatically delete original
        print("\n[+] Step 2: Select File to Encrypt")
        print("    1. Open graphical File Dialog Box (Recommended)")
        print("    2. Type file path manually")
        sub_choice = input("Select [1/2, default 1]: ").strip()

        selected_file = None
        if sub_choice in ("", "1"):
            print("[*] Opening file dialog box...")
            selected_file = select_file_via_dialog("Select file to encrypt")
            if not selected_file:
                selected_file = input("File path: ").strip().strip('"').strip("'")
        else:
            selected_file = input("File path: ").strip().strip('"').strip("'")

        if not selected_file or not os.path.isfile(selected_file):
            print(f"[!] Error: File not found or invalid: {selected_file}")
            sys.exit(1)

        p = Path(selected_file).resolve()
        default_dest = str(p.with_name(p.name + ".kromium"))
        dest_input = input(f"\nEnter destination path [Press Enter for '{default_dest}']: ").strip().strip('"').strip("'")
        destination = dest_input if dest_input else default_dest

        print("\n⚡ Note: The existing plaintext file will be automatically securely shredded & deleted once encrypted.")
        keep_input = input("Keep original file anyway? (y/N, default No): ").strip().lower()
        delete_source = keep_input != "y"

        print("\n[+] Step 3: Master Password")
        pwd_raw = getpass.getpass("Enter Master Password: ")
        if not pwd_raw:
            print("[!] Error: Password cannot be empty.")
            sys.exit(1)
        confirm_pwd = getpass.getpass("Confirm Master Password: ")
        if pwd_raw != confirm_pwd:
            print("[!] Error: Passwords do not match.")
            sys.exit(1)

        pwd_bytes = bytearray(pwd_raw.encode("utf-8"))
        del pwd_raw

        print("\n[*] Processing encryption & source file erasure...")
        try:
            encrypt_file(str(p), destination, pwd_bytes, iterations=DEFAULT_ITERATIONS, delete_source=delete_source)
            print(f"\n[✔] SUCCESS: File successfully encrypted to:")
            print(f"    {destination}")
            if delete_source:
                print(f"    ✔ Original file '{p.name}' was automatically securely shredded and deleted.")
        except Exception as e:
            print(f"\n[!] ERROR: Operation failed ({e})")
            sys.exit(1)
        finally:
            secure_wipe(pwd_bytes)
            print("[*] Memory sanitized: Master key and password buffers zeroized.")
        return

    else:
        # Decrypt .kromium file
        print("\n[+] Step 2: Select .kromium File to Decrypt")
        selected_file = select_file_via_dialog("Select .kromium file to decrypt")
        if not selected_file:
            selected_file = input("File path: ").strip().strip('"').strip("'")

        if not selected_file or not os.path.isfile(selected_file):
            print(f"[!] Error: File not found or invalid: {selected_file}")
            sys.exit(1)

        p = Path(selected_file).resolve()
        default_name = None
        try:
            meta = peek_container_metadata(str(p))
            orig = meta.get("original_filename")
            if orig and orig != p.name:
                default_name = orig
        except Exception:
            pass
        if not default_name:
            default_name = p.name[:-8] if p.name.lower().endswith(".kromium") else p.name + ".decrypted"

        default_dest = str(p.with_name(default_name))
        dest_input = input(f"\nEnter restore destination path [Press Enter for '{default_dest}']: ").strip().strip('"').strip("'")
        destination = dest_input if dest_input else default_dest

        print("\n⚡ Note: The .kromium container file will be automatically deleted once decryption succeeds.")
        keep_input = input("Keep .kromium file anyway? (y/N, default No): ").strip().lower()
        delete_source = keep_input != "y"

        pwd_raw = getpass.getpass("Enter Master Password: ")
        if not pwd_raw:
            print("[!] Error: Password cannot be empty.")
            sys.exit(1)

        pwd_bytes = bytearray(pwd_raw.encode("utf-8"))
        del pwd_raw

        print("\n[*] Decrypting container...")
        try:
            orig_name = decrypt_file(str(p), destination, pwd_bytes, delete_source=delete_source)
            print(f"\n[✔] SUCCESS: Container successfully decrypted to:")
            print(f"    {destination}")
            if orig_name:
                print(f"    (Embedded original filename: {orig_name})")
            if delete_source:
                print(f"    ✔ Encrypted container '{p.name}' was securely shredded and deleted.")
        except AuthenticationError:
            print("\n[!] AUTHENTICATION FAILED: Incorrect master password or file has been tampered with.")
            sys.exit(1)
        except Exception as e:
            print(f"\n[!] ERROR: Decryption failed ({e})")
            sys.exit(1)
        finally:
            secure_wipe(pwd_bytes)
            print("[*] Memory sanitized: Master key and password buffers zeroized.")


def handle_cli_arguments():
    """Parses command-line flags for scriptable execution or inspection."""
    parser = argparse.ArgumentParser(
        description="Kromium Vault - Authenticated File Encryption & Decryption (.kromium)"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-t", "--text", metavar="TEXT", help="Encrypt sensitive text string directly into a .kromium container")
    group.add_argument("-e", "--encrypt", metavar="FILE", help="Encrypt target file to .kromium container (Auto-deletes original)")
    group.add_argument("-d", "--decrypt", metavar="KROMIUM_FILE", help="Decrypt .kromium container file")
    group.add_argument("-i", "--info", metavar="KROMIUM_FILE", help="Inspect container header metadata without decrypting")
    group.add_argument("--interactive", action="store_true", help="Launch interactive CLI workflow")

    parser.add_argument("-o", "--output", metavar="DEST", help="Custom destination path")
    parser.add_argument("--keep-source", action="store_true", help="Do not delete the original file when encrypting")
    parser.add_argument("--view", action="store_true", help="Print decrypted text directly to terminal without saving to disk")

    args = parser.parse_args()

    if args.info:
        try:
            meta = peek_container_metadata(args.info)
            print("=" * 50)
            print(f"  Container: {meta['file_name']}")
            print(f"  Format Version: v{meta['format_version']}")
            print(f"  PBKDF2 Rounds:  {meta['kdf_iterations']:,}")
            print(f"  Salt (Hex):     {meta['salt_hex']}")
            print(f"  Nonce (Hex):    {meta['nonce_hex']}")
            print(f"  Original Name:  {meta.get('original_filename') or 'None'}")
            print(f"  Ciphertext:     {meta['ciphertext_bytes']} bytes")
            print("=" * 50)
            return
        except Exception as e:
            print(f"[!] Error inspecting container: {e}")
            sys.exit(1)

    if args.text:
        dest = args.output or "vault_secret.kromium"
        if not dest.lower().endswith(".kromium"):
            dest += ".kromium"

        pwd_raw = getpass.getpass("Enter Master Password: ")
        if not pwd_raw:
            print("[!] Error: Password cannot be empty.")
            sys.exit(1)
        pwd_bytes = bytearray(pwd_raw.encode("utf-8"))
        del pwd_raw

        try:
            encrypt_text_to_file(args.text, dest, pwd_bytes)
            print(f"[✔] Successfully created .kromium file from text at: {dest}")
        except Exception as e:
            print(f"[!] Encryption failed: {e}")
            sys.exit(1)
        finally:
            secure_wipe(pwd_bytes)
        return

    if args.encrypt:
        src = args.encrypt
        p = Path(src).resolve()
        if not p.is_file():
            print(f"[!] Error: File not found: {src}")
            sys.exit(1)

        dest = args.output or str(p.with_name(p.name + ".kromium"))
        delete_source = not args.keep_source

        pwd_raw = getpass.getpass("Enter Master Password: ")
        if not pwd_raw:
            print("[!] Error: Password cannot be empty.")
            sys.exit(1)
        pwd_bytes = bytearray(pwd_raw.encode("utf-8"))
        del pwd_raw

        try:
            encrypt_file(str(p), dest, pwd_bytes, delete_source=delete_source)
            print(f"[✔] Successfully encrypted to: {dest}")
            if delete_source:
                print(f"✔ Original file '{p.name}' was securely shredded and deleted.")
        except AuthenticationError:
            print("[!] Authentication Failed: Invalid password or corrupted/tampered file.")
            sys.exit(1)
        except Exception as e:
            print(f"[!] Operation Failed: {e}")
            sys.exit(1)
        finally:
            secure_wipe(pwd_bytes)
        return

    if args.decrypt:
        src = args.decrypt
        p = Path(src).resolve()
        if not p.is_file():
            print(f"[!] Error: File not found: {src}")
            sys.exit(1)

        delete_source = not args.keep_source

        pwd_raw = getpass.getpass("Enter Master Password: ")
        if not pwd_raw:
            print("[!] Error: Password cannot be empty.")
            sys.exit(1)
        pwd_bytes = bytearray(pwd_raw.encode("utf-8"))
        del pwd_raw

        try:
            if args.view:
                text, orig = decrypt_file_to_text(str(p), pwd_bytes, delete_source=delete_source)
                print(f"\n--- Decrypted Content (Original: {orig}) ---")
                print(text)
                print("---------------------------------------------")
                if delete_source:
                    print(f"✔ Encrypted container '{p.name}' was securely shredded and deleted.")
            else:
                dest = args.output
                if not dest:
                    try:
                        meta = peek_container_metadata(str(p))
                        dest = str(p.with_name(meta.get("original_filename") or (p.name[:-8] if p.name.endswith(".kromium") else p.name + ".dec")))
                    except Exception:
                        dest = str(p.with_name(p.name[:-8] if p.name.endswith(".kromium") else p.name + ".dec"))
                orig = decrypt_file(str(p), dest, pwd_bytes, delete_source=delete_source)
                print(f"[✔] Successfully decrypted to: {dest} (Original: {orig})")
                if delete_source:
                    print(f"✔ Encrypted container '{p.name}' was securely shredded and deleted.")
        except AuthenticationError:
            print("[!] Authentication Failed: Invalid password or corrupted/tampered file.")
            sys.exit(1)
        except Exception as e:
            print(f"[!] Operation Failed: {e}")
            sys.exit(1)
        finally:
            secure_wipe(pwd_bytes)
        return

    interactive_workflow()


if __name__ == "__main__":
    handle_cli_arguments()
