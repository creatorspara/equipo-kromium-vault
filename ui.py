"""
Equipo Kromium Vault - Desktop GUI Application (ui.py)
======================================================
Senior Security Engineer Implementation
Brand Kit: Equipo Kromium (Build · Open · Share)
Theme:
- Primary Violet: #6C4DFF
- Lavender Accent: #A78BFA
- Light Accent: #D1C4FF
- Base Dark: #0A0A0F
- Card Surface: #12121A
- Border: #2A2640
- Text Primary: #F5F5F7
- Typography: Sora / Segoe UI
"""

import os
import re
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, Dict, Any

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


# ---------------------------------------------------------------------------
# Equipo Kromium Brand Palette
# ---------------------------------------------------------------------------
COLOR_BASE_DARK = "#0A0A0F"       # Official brand dark background
COLOR_CARD_BG = "#12121A"         # Card surface
COLOR_CARD_HEADER = "#161622"     # Section card header
COLOR_INPUT_BG = "#0D0D14"        # Input fields background
COLOR_BORDER = "#2A2640"          # Violet-tinted border lines
COLOR_TEXT_PRIMARY = "#F5F5F7"    # Off-white primary text
COLOR_TEXT_MUTED = "#9D9AA8"      # Subdued secondary text

COLOR_KROMIUM_PURPLE = "#6C4DFF"  # Primary Brand Purple
COLOR_KROMIUM_LAVENDER = "#A78BFA"# Secondary Lavender
COLOR_KROMIUM_LIGHT = "#D1C4FF"   # Light Accent
COLOR_KROMIUM_HOVER = "#5838E6"   # Button active / hover

COLOR_SUCCESS = "#10B981"         # Emerald success
COLOR_WARNING = "#F59E0B"         # Amber warning
COLOR_DANGER = "#EF4444"          # Crimson error

FONT_FAMILY = "Sora" if "Sora" in ["Sora"] else ("Segoe UI" if sys.platform == "win32" else "Helvetica")
ASSETS_DIR = Path(__file__).resolve().parent / "assets"


class KromiumApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Equipo Kromium Vault - Authenticated File Security")
        self.geometry("840x880")
        self.minsize(760, 800)
        self.configure(bg=COLOR_BASE_DARK)

        # Set application icon if available
        self._set_window_icon()

        # Application state
        self.current_mode = tk.StringVar(value="encrypt")           # 'encrypt' or 'decrypt'
        self.encrypt_source_type = tk.StringVar(value="text")       # 'text' (direct entry) or 'file' (disk file)
        self.selected_file_path = tk.StringVar(value="")
        self.output_file_path = tk.StringVar(value="")
        self.show_password = tk.BooleanVar(value=False)
        self.auto_delete_source = tk.BooleanVar(value=True)         # Auto delete original file when encryption is done
        self.is_processing = False

        self._init_styles()
        self._build_ui()
        self._update_mode_view()

    def _set_window_icon(self):
        """Sets window taskbar and title icon from generated brand assets."""
        try:
            ico_path = ASSETS_DIR / "app_icon.ico"
            if ico_path.is_file():
                self.iconbitmap(default=str(ico_path))
            png_path = ASSETS_DIR / "app_icon.png"
            if png_path.is_file():
                self._icon_img = tk.PhotoImage(file=str(png_path))
                self.iconphoto(False, self._icon_img)
        except Exception:
            pass

    def _init_styles(self):
        """Initializes ttk styles to match the Equipo Kromium brand palette."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TProgressbar",
            troughcolor=COLOR_BASE_DARK,
            background=COLOR_KROMIUM_PURPLE,
            thickness=6,
            borderwidth=0
        )

    def _build_ui(self):
        """Constructs the desktop GUI layout reflecting the brand kit."""
        # Top Brand Banner
        banner_frame = tk.Frame(self, bg=COLOR_CARD_BG, highlightthickness=1, highlightbackground=COLOR_BORDER)
        banner_frame.pack(fill="x", padx=16, pady=(14, 8))

        title_box = tk.Frame(banner_frame, bg=COLOR_CARD_BG)
        title_box.pack(fill="x", padx=20, pady=14)

        # Brand header with monogram symbol & wordmark
        header_row = tk.Frame(title_box, bg=COLOR_CARD_BG)
        header_row.pack(fill="x")

        # Monogram aesthetic symbol
        logo_symbol = tk.Label(
            header_row,
            text="⚡",
            font=(FONT_FAMILY, 20, "bold"),
            fg=COLOR_KROMIUM_PURPLE,
            bg=COLOR_CARD_BG
        )
        logo_symbol.pack(side="left", padx=(0, 10))

        title_text_box = tk.Frame(header_row, bg=COLOR_CARD_BG)
        title_text_box.pack(side="left")

        title_lbl = tk.Label(
            title_text_box,
            text="Equipo Kromium Vault",
            font=(FONT_FAMILY, 16, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD_BG
        )
        title_lbl.pack(anchor="w")

        tagline_lbl = tk.Label(
            title_text_box,
            text="Build  •  Open  •  Share",
            font=(FONT_FAMILY, 9, "bold"),
            fg=COLOR_KROMIUM_LAVENDER,
            bg=COLOR_CARD_BG
        )
        tagline_lbl.pack(anchor="w", pady=(1, 0))

        # Community pill badge
        community_badge = tk.Label(
            header_row,
            text="Open Source Security",
            font=(FONT_FAMILY, 8, "bold"),
            fg=COLOR_KROMIUM_LIGHT,
            bg="#211A40",
            padx=10,
            pady=4,
            relief="flat"
        )
        community_badge.pack(side="right")

        # Description line from brand kit
        desc_lbl = tk.Label(
            title_box,
            text="A student led developer team building open source software for a stronger, more open tech community.",
            font=(FONT_FAMILY, 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD_BG,
            anchor="w"
        )
        desc_lbl.pack(anchor="w", pady=(8, 0))

        # Main scrollable or card container
        main_container = tk.Frame(self, bg=COLOR_BASE_DARK)
        main_container.pack(fill="both", expand=True, padx=16, pady=2)

        # ---------------------------------------------------------
        # Section 1: Operation Mode & Input Type
        # ---------------------------------------------------------
        mode_card = self._create_card(main_container, "STEP 1: OPERATION & INPUT TYPE")
        mode_card.pack(fill="x", pady=4)

        mode_btn_box = tk.Frame(mode_card, bg=COLOR_CARD_BG)
        mode_btn_box.pack(fill="x", padx=16, pady=(6, 8))

        self.rb_encrypt = tk.Radiobutton(
            mode_btn_box,
            text="🔒 Encrypt & Create .kromium File",
            variable=self.current_mode,
            value="encrypt",
            command=self._on_mode_toggled,
            font=(FONT_FAMILY, 10, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD_BG,
            selectcolor="#211A40",
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_TEXT_PRIMARY
        )
        self.rb_encrypt.pack(side="left", padx=(0, 24))

        self.rb_decrypt = tk.Radiobutton(
            mode_btn_box,
            text="🔓 Decrypt .kromium File",
            variable=self.current_mode,
            value="decrypt",
            command=self._on_mode_toggled,
            font=(FONT_FAMILY, 10, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD_BG,
            selectcolor="#211A40",
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_TEXT_PRIMARY
        )
        self.rb_decrypt.pack(side="left")

        # Sub-selector for Encryption Source (Direct Text vs File on Disk)
        self.enc_source_frame = tk.Frame(mode_card, bg="#181628", padx=12, pady=6)
        self.enc_source_frame.pack(fill="x", padx=16, pady=(0, 10))

        enc_source_lbl = tk.Label(
            self.enc_source_frame,
            text="Source:",
            font=(FONT_FAMILY, 8, "bold"),
            fg=COLOR_KROMIUM_LAVENDER,
            bg="#181628"
        )
        enc_source_lbl.pack(side="left", padx=(0, 12))

        self.rb_src_text = tk.Radiobutton(
            self.enc_source_frame,
            text="📝 Enter Sensitive Text Directly (Auto-creates .kromium)",
            variable=self.encrypt_source_type,
            value="text",
            command=self._on_source_type_toggled,
            font=(FONT_FAMILY, 9),
            fg=COLOR_TEXT_PRIMARY,
            bg="#181628",
            selectcolor="#0D0D14",
            activebackground="#181628",
            activeforeground=COLOR_TEXT_PRIMARY
        )
        self.rb_src_text.pack(side="left", padx=(0, 16))

        self.rb_src_file = tk.Radiobutton(
            self.enc_source_frame,
            text="📁 Select File from Disk (Auto-deletes original)",
            variable=self.encrypt_source_type,
            value="file",
            command=self._on_source_type_toggled,
            font=(FONT_FAMILY, 9),
            fg=COLOR_TEXT_PRIMARY,
            bg="#181628",
            selectcolor="#0D0D14",
            activebackground="#181628",
            activeforeground=COLOR_TEXT_PRIMARY
        )
        self.rb_src_file.pack(side="left")

        # ---------------------------------------------------------
        # Section 2: Input Content / File Selection
        # ---------------------------------------------------------
        self.content_card = self._create_card(main_container, "STEP 2: DATA & DESTINATION")
        self.content_card.pack(fill="x", pady=4)

        # Dynamic subframe A: Direct Text Input Area
        self.text_input_frame = tk.Frame(self.content_card, bg=COLOR_CARD_BG)
        self.text_input_frame.pack(fill="x", padx=16, pady=(4, 6))

        text_label_row = tk.Frame(self.text_input_frame, bg=COLOR_CARD_BG)
        text_label_row.pack(fill="x")
        
        tk.Label(
            text_label_row,
            text="Enter Sensitive Text / Passwords to Encrypt:",
            font=(FONT_FAMILY, 9, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD_BG
        ).pack(side="left")

        tk.Label(
            text_label_row,
            text="(Automatically generates a secure .kromium container)",
            font=(FONT_FAMILY, 8),
            fg=COLOR_KROMIUM_LAVENDER,
            bg=COLOR_CARD_BG
        ).pack(side="left", padx=8)

        self.text_editor = tk.Text(
            self.text_input_frame,
            height=6,
            font=("Consolas", 10),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_KROMIUM_LIGHT,
            relief="solid",
            bd=1,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            wrap="word"
        )
        self.text_editor.pack(fill="x", pady=(4, 2))

        # Dynamic subframe B: File on Disk Row
        self.file_input_frame = tk.Frame(self.content_card, bg=COLOR_CARD_BG)

        self.src_label_row = tk.Frame(self.file_input_frame, bg=COLOR_CARD_BG)
        self.src_label_row.pack(fill="x", pady=(0, 2))
        
        self.src_file_label = tk.Label(
            self.src_label_row,
            text="Source File:",
            font=(FONT_FAMILY, 9, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD_BG
        )
        self.src_file_label.pack(side="left")

        src_input_row = tk.Frame(self.file_input_frame, bg=COLOR_CARD_BG)
        src_input_row.pack(fill="x", pady=(0, 4))

        self.src_entry = tk.Entry(
            src_input_row,
            textvariable=self.selected_file_path,
            font=(FONT_FAMILY, 9),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_KROMIUM_LIGHT,
            relief="solid",
            bd=1,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1
        )
        self.src_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))

        browse_src_btn = tk.Button(
            src_input_row,
            text="📂 Browse...",
            command=self._browse_source_file,
            font=(FONT_FAMILY, 9, "bold"),
            bg="#211A40",
            fg=COLOR_KROMIUM_LIGHT,
            activebackground=COLOR_KROMIUM_PURPLE,
            activeforeground=COLOR_TEXT_PRIMARY,
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2"
        )
        browse_src_btn.pack(side="right")

        self.info_box = tk.Label(
            self.file_input_frame,
            text="Select a file to inspect its parameters.",
            font=(FONT_FAMILY, 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD_BG,
            anchor="w",
            justify="left"
        )
        self.info_box.pack(fill="x", pady=(0, 4))

        # Destination Output File Row
        self.dest_container = tk.Frame(self.content_card, bg=COLOR_CARD_BG)
        self.dest_container.pack(fill="x", padx=16, pady=(4, 6))

        dest_label_row = tk.Frame(self.dest_container, bg=COLOR_CARD_BG)
        dest_label_row.pack(fill="x", pady=(2, 2))
        
        self.dest_file_label = tk.Label(
            dest_label_row,
            text="Destination .kromium Container File:",
            font=(FONT_FAMILY, 9, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD_BG
        )
        self.dest_file_label.pack(side="left")

        dest_input_row = tk.Frame(self.dest_container, bg=COLOR_CARD_BG)
        dest_input_row.pack(fill="x", pady=(0, 6))

        self.dest_entry = tk.Entry(
            dest_input_row,
            textvariable=self.output_file_path,
            font=(FONT_FAMILY, 9),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_KROMIUM_LIGHT,
            relief="solid",
            bd=1,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1
        )
        self.dest_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))

        self.browse_dest_btn = tk.Button(
            dest_input_row,
            text="💾 Save As...",
            command=self._browse_destination_file,
            font=(FONT_FAMILY, 9, "bold"),
            bg="#211A40",
            fg=COLOR_KROMIUM_LIGHT,
            activebackground=COLOR_KROMIUM_PURPLE,
            activeforeground=COLOR_TEXT_PRIMARY,
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2"
        )
        self.browse_dest_btn.pack(side="right")

        # Plaintext viewer row for Decrypt mode
        self.decrypt_view_frame = tk.Frame(self.content_card, bg=COLOR_CARD_BG)
        dec_view_header = tk.Frame(self.decrypt_view_frame, bg=COLOR_CARD_BG)
        dec_view_header.pack(fill="x")
        
        tk.Label(
            dec_view_header,
            text="Decrypted Plaintext Viewer:",
            font=(FONT_FAMILY, 9, "bold"),
            fg=COLOR_KROMIUM_LAVENDER,
            bg=COLOR_CARD_BG
        ).pack(side="left")

        copy_btn = tk.Button(
            dec_view_header,
            text="📋 Copy to Clipboard",
            command=self._copy_decrypted_text,
            font=(FONT_FAMILY, 8, "bold"),
            bg="#211A40",
            fg=COLOR_TEXT_PRIMARY,
            activebackground=COLOR_KROMIUM_PURPLE,
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2"
        )
        copy_btn.pack(side="right", padx=(4, 0))

        clear_view_btn = tk.Button(
            dec_view_header,
            text="❌ Clear View",
            command=self._clear_decrypted_view,
            font=(FONT_FAMILY, 8),
            bg="#1A1828",
            fg=COLOR_TEXT_MUTED,
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2"
        )
        clear_view_btn.pack(side="right")

        self.decrypted_text_viewer = tk.Text(
            self.decrypt_view_frame,
            height=5,
            font=("Consolas", 10),
            bg=COLOR_INPUT_BG,
            fg=COLOR_KROMIUM_LIGHT,
            insertbackground=COLOR_TEXT_PRIMARY,
            relief="solid",
            bd=1,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            wrap="word"
        )
        self.decrypted_text_viewer.pack(fill="x", pady=(4, 4))

        # ---------------------------------------------------------
        # Section 3: Password & Access Control
        # ---------------------------------------------------------
        pwd_card = self._create_card(main_container, "STEP 3: ACCESS CONTROL & CREDENTIALS")
        pwd_card.pack(fill="x", pady=4)

        pwd_label_row = tk.Frame(pwd_card, bg=COLOR_CARD_BG)
        pwd_label_row.pack(fill="x", padx=16, pady=(6, 2))
        
        pwd_label = tk.Label(
            pwd_label_row,
            text="Master Password:",
            font=(FONT_FAMILY, 9, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD_BG
        )
        pwd_label.pack(side="left")

        pwd_input_row = tk.Frame(pwd_card, bg=COLOR_CARD_BG)
        pwd_input_row.pack(fill="x", padx=16, pady=(0, 4))

        self.pwd_entry = tk.Entry(
            pwd_input_row,
            show="*",
            font=(FONT_FAMILY, 10),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_KROMIUM_LIGHT,
            relief="solid",
            bd=1,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1
        )
        self.pwd_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))
        self.pwd_entry.bind("<KeyRelease>", self._on_password_changed)

        self.toggle_pwd_btn = tk.Button(
            pwd_input_row,
            text="👁 Show",
            command=self._toggle_password_visibility,
            font=(FONT_FAMILY, 8, "bold"),
            bg="#211A40",
            fg=COLOR_KROMIUM_LIGHT,
            activebackground=COLOR_KROMIUM_PURPLE,
            activeforeground=COLOR_TEXT_PRIMARY,
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2"
        )
        self.toggle_pwd_btn.pack(side="right")

        # Confirm Password Row
        self.confirm_frame = tk.Frame(pwd_card, bg=COLOR_CARD_BG)
        self.confirm_frame.pack(fill="x", padx=16, pady=(2, 4))

        confirm_label = tk.Label(
            self.confirm_frame,
            text="Confirm Master Password:",
            font=(FONT_FAMILY, 9, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD_BG
        )
        confirm_label.pack(anchor="w", pady=(0, 2))

        self.confirm_pwd_entry = tk.Entry(
            self.confirm_frame,
            show="*",
            font=(FONT_FAMILY, 10),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_KROMIUM_LIGHT,
            relief="solid",
            bd=1,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1
        )
        self.confirm_pwd_entry.pack(fill="x", ipady=4)
        self.confirm_pwd_entry.bind("<KeyRelease>", self._on_password_changed)

        # Password Strength Indicator
        self.strength_frame = tk.Frame(pwd_card, bg=COLOR_CARD_BG)
        self.strength_frame.pack(fill="x", padx=16, pady=(2, 4))

        strength_header = tk.Frame(self.strength_frame, bg=COLOR_CARD_BG)
        strength_header.pack(fill="x")
        
        strength_title = tk.Label(
            strength_header,
            text="Entropy Strength:",
            font=(FONT_FAMILY, 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD_BG
        )
        strength_title.pack(side="left")

        self.strength_text = tk.Label(
            strength_header,
            text="Empty",
            font=(FONT_FAMILY, 8, "bold"),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD_BG
        )
        self.strength_text.pack(side="right")

        self.strength_canvas = tk.Canvas(self.strength_frame, height=5, bg="#1E1A2E", highlightthickness=0)
        self.strength_canvas.pack(fill="x", pady=(2, 2))
        self.strength_bar = self.strength_canvas.create_rectangle(0, 0, 0, 5, fill="#1E1A2E", width=0)

        # Auto-delete original file checkbox
        self.delete_frame = tk.Frame(pwd_card, bg=COLOR_CARD_BG)
        self.delete_cb = tk.Checkbutton(
            self.delete_frame,
            text="🗑️ Automatically delete & securely shred existing plaintext file once encryption is done",
            variable=self.auto_delete_source,
            font=(FONT_FAMILY, 8, "bold"),
            fg=COLOR_KROMIUM_LAVENDER,
            bg=COLOR_CARD_BG,
            selectcolor="#211A40",
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_KROMIUM_LIGHT
        )
        self.delete_cb.pack(anchor="w", padx=16, pady=(2, 6))

        # ---------------------------------------------------------
        # Section 4: Execution & Feedback
        # ---------------------------------------------------------
        action_box = tk.Frame(main_container, bg=COLOR_BASE_DARK)
        action_box.pack(fill="x", pady=(8, 2))

        self.progress_bar = ttk.Progressbar(action_box, mode="indeterminate", style="TProgressbar")
        self.progress_bar.pack(fill="x", pady=(0, 8))

        self.action_btn = tk.Button(
            action_box,
            text="🔒 ENCRYPT TEXT & GENERATE .KROMIUM FILE",
            command=self._execute_action,
            font=(FONT_FAMILY, 11, "bold"),
            bg=COLOR_KROMIUM_PURPLE,
            fg=COLOR_TEXT_PRIMARY,
            activebackground=COLOR_KROMIUM_HOVER,
            activeforeground=COLOR_TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            pady=10
        )
        self.action_btn.pack(fill="x")

        # Status Bar at Bottom
        status_bar = tk.Frame(self, bg=COLOR_CARD_BG, highlightthickness=1, highlightbackground=COLOR_BORDER)
        status_bar.pack(fill="x", side="bottom")

        self.status_lbl = tk.Label(
            status_bar,
            text="Equipo Kromium • Ready. Enter sensitive text to create a .kromium file or select a file to encrypt/decrypt.",
            font=(FONT_FAMILY, 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD_BG,
            padx=12,
            pady=6,
            anchor="w"
        )
        self.status_lbl.pack(fill="x")

    def _create_card(self, parent: tk.Widget, title: str) -> tk.Frame:
        """Helper to create visually structured card frames matching the brand kit."""
        card = tk.Frame(parent, bg=COLOR_CARD_BG, highlightthickness=1, highlightbackground=COLOR_BORDER)
        title_lbl = tk.Label(
            card,
            text=title,
            font=(FONT_FAMILY, 8, "bold"),
            fg=COLOR_KROMIUM_LAVENDER,
            bg=COLOR_CARD_BG
        )
        title_lbl.pack(anchor="w", padx=16, pady=(8, 4))
        return card

    # -----------------------------------------------------------------------
    # Dynamic View State Management
    # -----------------------------------------------------------------------
    def _on_mode_toggled(self):
        self._update_mode_view()

    def _on_source_type_toggled(self):
        self._update_mode_view()

    def _update_mode_view(self):
        mode = self.current_mode.get()
        src_type = self.encrypt_source_type.get()

        if mode == "encrypt":
            self.enc_source_frame.pack(fill="x", padx=16, pady=(0, 10))
            self.confirm_frame.pack(fill="x", padx=16, pady=(2, 4))
            self.strength_frame.pack(fill="x", padx=16, pady=(2, 4))
            self.decrypt_view_frame.pack_forget()

            if src_type == "text":
                self.text_input_frame.pack(fill="x", padx=16, pady=(4, 6))
                self.file_input_frame.pack_forget()
                self.delete_frame.pack_forget()
                self.dest_file_label.config(text="Save New .kromium Container As:")
                self.action_btn.config(
                    text="🔒 ENCRYPT TEXT & CREATE .KROMIUM FILE",
                    bg=COLOR_KROMIUM_PURPLE,
                    activebackground=COLOR_KROMIUM_HOVER
                )
                if not self.output_file_path.get() or not self.output_file_path.get().endswith(".kromium"):
                    self.output_file_path.set(str(Path.cwd() / "kromium_vault.kromium"))
            else:
                self.text_input_frame.pack_forget()
                self.file_input_frame.pack(fill="x", padx=16, pady=(4, 6))
                self.delete_frame.pack(fill="x")
                self.delete_cb.config(text="🗑️ Automatically delete & securely shred existing plaintext file once encryption is done")
                self.src_file_label.config(text="Source File to Encrypt:")
                self.dest_file_label.config(text="Destination .kromium Container File:")
                self.action_btn.config(
                    text="🔒 ENCRYPT FILE & DELETE EXISTING ORIGINAL",
                    bg=COLOR_KROMIUM_PURPLE,
                    activebackground=COLOR_KROMIUM_HOVER
                )
                self._update_destination_suggestion()
        else:
            self.enc_source_frame.pack_forget()
            self.text_input_frame.pack_forget()
            self.confirm_frame.pack_forget()
            self.strength_frame.pack_forget()

            self.file_input_frame.pack(fill="x", padx=16, pady=(4, 6))
            self.delete_frame.pack(fill="x")
            self.delete_cb.config(text="🗑️ Automatically delete & securely shred .kromium file once decryption succeeds")
            self.src_file_label.config(text="Encrypted .kromium File:")
            self.dest_file_label.config(text="Restore Decrypted Plaintext To:")
            self.decrypt_view_frame.pack(fill="x", padx=16, pady=(4, 8))

            self.action_btn.config(
                text="🔓 DECRYPT .KROMIUM FILE & DELETE CONTAINER",
                bg="#4F35C7",
                activebackground=COLOR_KROMIUM_PURPLE
            )
            self._update_destination_suggestion()

    def _toggle_password_visibility(self):
        show = not self.show_password.get()
        self.show_password.set(show)
        mask = "" if show else "*"
        self.pwd_entry.config(show=mask)
        self.confirm_pwd_entry.config(show=mask)
        self.toggle_pwd_btn.config(text="🙈 Hide" if show else "👁 Show")

    def _browse_source_file(self):
        mode = self.current_mode.get()
        if mode == "decrypt":
            filetypes = [
                ("Kromium Vault Files (*.kromium)", "*.kromium"),
                ("All Files (*.*)", "*.*")
            ]
        else:
            filetypes = [
                ("All Files (*.*)", "*.*"),
                ("Kromium Vault Files (*.kromium)", "*.kromium")
            ]

        chosen = filedialog.askopenfilename(
            title="Select Target File",
            filetypes=filetypes
        )
        if not chosen:
            return

        self.selected_file_path.set(chosen)
        p = Path(chosen)

        if p.name.lower().endswith(".kromium") and mode == "encrypt":
            self.current_mode.set("decrypt")
            self._update_mode_view()
        elif not p.name.lower().endswith(".kromium") and mode == "decrypt":
            self.current_mode.set("encrypt")
            self.encrypt_source_type.set("file")
            self._update_mode_view()

        self._inspect_selected_file()
        self._update_destination_suggestion()

    def _browse_destination_file(self):
        mode = self.current_mode.get()
        current_dest = self.output_file_path.get()
        init_file = os.path.basename(current_dest) if current_dest else ("vault_secret.kromium" if mode == "encrypt" else "")
        init_dir = os.path.dirname(current_dest) if current_dest else str(Path.cwd())

        if mode == "encrypt":
            filetypes = [
                ("Kromium Vault Files (*.kromium)", "*.kromium"),
                ("All Files (*.*)", "*.*")
            ]
            default_ext = ".kromium"
        else:
            filetypes = [("All Files (*.*)", "*.*")]
            default_ext = ""

        chosen = filedialog.asksaveasfilename(
            title="Choose Destination File",
            initialdir=init_dir,
            initialfile=init_file,
            defaultextension=default_ext,
            filetypes=filetypes
        )
        if chosen:
            self.output_file_path.set(chosen)

    def _inspect_selected_file(self):
        path_str = self.selected_file_path.get()
        if not path_str or not os.path.isfile(path_str):
            self.info_box.config(text="Select a file to inspect its parameters.", fg=COLOR_TEXT_MUTED)
            return

        p = Path(path_str)
        size_kb = p.stat().st_size / 1024

        if p.name.lower().endswith(".kromium"):
            try:
                meta = peek_container_metadata(path_str)
                orig = meta.get("original_filename") or "(Unspecified)"
                iters = meta.get("kdf_iterations", DEFAULT_ITERATIONS)
                self.info_box.config(
                    text=f"✔ Valid .kromium v{meta['format_version']} Container  |  Size: {size_kb:.1f} KB\n"
                         f"Original Name: {orig}  |  KDF Rounds: {iters:,}  |  Salt: {meta['salt_hex'][:16]}...",
                    fg=COLOR_KROMIUM_LIGHT
                )
                return
            except InvalidHeaderError:
                self.info_box.config(
                    text="⚠️ Warning: File has .kromium extension but header magic is invalid or corrupted.",
                    fg=COLOR_DANGER
                )
                return
            except Exception as e:
                self.info_box.config(
                    text=f"⚠️ Unable to parse container metadata: {str(e)}",
                    fg=COLOR_WARNING
                )
                return

        self.info_box.config(
            text=f"Target: {p.name}  |  Plaintext Size: {size_kb:.1f} KB  |  Ready to encrypt",
            fg=COLOR_TEXT_MUTED
        )

    def _update_destination_suggestion(self):
        mode = self.current_mode.get()
        src = self.selected_file_path.get()

        if mode == "encrypt":
            if self.encrypt_source_type.get() == "text":
                if not self.output_file_path.get():
                    self.output_file_path.set(str(Path.cwd() / "kromium_vault.kromium"))
                return

            if not src:
                return
            p = Path(src)
            if not p.name.lower().endswith(".kromium"):
                suggested = str(p.with_name(p.name + ".kromium"))
            else:
                suggested = str(p.with_name(p.name + ".enc.kromium"))
            self.output_file_path.set(suggested)
        else:
            if not src:
                return
            p = Path(src)
            suggested_name = None
            try:
                if p.is_file():
                    meta = peek_container_metadata(src)
                    orig = meta.get("original_filename")
                    if orig and orig != p.name:
                        suggested_name = orig
            except Exception:
                pass

            if not suggested_name:
                if p.name.lower().endswith(".kromium"):
                    suggested_name = p.name[:-8]
                else:
                    suggested_name = p.name + ".decrypted"

            suggested = str(p.with_name(suggested_name))
            self.output_file_path.set(suggested)

    def _on_password_changed(self, event=None):
        pwd = self.pwd_entry.get()
        if not pwd:
            self.strength_canvas.coords(self.strength_bar, 0, 0, 0, 5)
            self.strength_text.config(text="Empty", fg=COLOR_TEXT_MUTED)
            return

        score = 0
        length = len(pwd)
        if length >= 8:
            score += 1
        if length >= 12:
            score += 1
        if length >= 16:
            score += 1
        if re.search(r"[a-z]", pwd) and re.search(r"[A-Z]", pwd):
            score += 1
        if re.search(r"\d", pwd):
            score += 1
        if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", pwd):
            score += 1

        width = self.strength_canvas.winfo_width() or 200
        if score <= 2:
            pct = 0.25
            color = COLOR_DANGER
            label = "Weak (Minimum 12+ mixed characters recommended)"
        elif score <= 4:
            pct = 0.55
            color = COLOR_WARNING
            label = "Moderate (Consider adding numbers and symbols)"
        elif score <= 5:
            pct = 0.80
            color = COLOR_KROMIUM_LAVENDER
            label = "Strong"
        else:
            pct = 1.0
            color = COLOR_KROMIUM_LIGHT
            label = "Hardened (Equipo Kromium Standard)"

        self.strength_canvas.coords(self.strength_bar, 0, 0, width * pct, 5)
        self.strength_canvas.itemconfig(self.strength_bar, fill=color)
        self.strength_text.config(text=label, fg=color)

    def _copy_decrypted_text(self):
        text = self.decrypted_text_viewer.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status_lbl.config(text="Decrypted text copied to clipboard.", fg=COLOR_KROMIUM_LIGHT)

    def _clear_decrypted_view(self):
        self.decrypted_text_viewer.delete("1.0", tk.END)
        self.status_lbl.config(text="Decrypted viewer cleared.", fg=COLOR_TEXT_MUTED)

    # -----------------------------------------------------------------------
    # Cryptographic Execution
    # -----------------------------------------------------------------------
    def _execute_action(self):
        if self.is_processing:
            return

        mode = self.current_mode.get()
        src_type = self.encrypt_source_type.get()
        dest = self.output_file_path.get().strip()

        if not dest:
            messagebox.showwarning("Missing Destination", "Please specify a destination file path.")
            return

        plaintext_text = ""
        src_file = ""
        if mode == "encrypt":
            if src_type == "text":
                plaintext_text = self.text_editor.get("1.0", tk.END).strip()
                if not plaintext_text:
                    messagebox.showwarning("Missing Input", "Please enter the sensitive text to encrypt.")
                    return
                if not dest.lower().endswith(".kromium"):
                    dest += ".kromium"
                    self.output_file_path.set(dest)
            else:
                src_file = self.selected_file_path.get().strip()
                if not src_file:
                    messagebox.showwarning("Missing Input", "Please select a source file to encrypt.")
                    return
                if not os.path.isfile(src_file):
                    messagebox.showerror("File Error", f"Source file does not exist:\n{src_file}")
                    return
                if os.path.abspath(src_file) == os.path.abspath(dest):
                    messagebox.showerror("Conflict", "Source and destination cannot be identical.")
                    return
        else:
            src_file = self.selected_file_path.get().strip()
            if not src_file:
                messagebox.showwarning("Missing Input", "Please select a .kromium file to decrypt.")
                return
            if not os.path.isfile(src_file):
                messagebox.showerror("File Error", f"Selected file does not exist:\n{src_file}")
                return

        pwd_str = self.pwd_entry.get()
        if not pwd_str:
            messagebox.showwarning("Password Required", "Please enter a master password.")
            return

        if mode == "encrypt":
            confirm_str = self.confirm_pwd_entry.get()
            if pwd_str != confirm_str:
                messagebox.showerror("Password Mismatch", "Passwords do not match. Please verify your master password.")
                return

        pwd_bytes = bytearray(pwd_str.encode("utf-8"))
        if mode == "encrypt":
            delete_source = self.auto_delete_source.get() and src_type == "file"
        else:
            delete_source = self.auto_delete_source.get()

        self.is_processing = True
        self.action_btn.config(state="disabled")
        self.progress_bar.start(10)
        self.status_lbl.config(
            text=f"Equipo Kromium Security Engine • Processing {mode} (600,000 PBKDF2 rounds)...",
            fg=COLOR_KROMIUM_LAVENDER
        )

        t = threading.Thread(
            target=self._worker_thread,
            args=(mode, src_type, src_file, dest, plaintext_text, pwd_bytes, delete_source),
            daemon=True
        )
        t.start()

    def _worker_thread(
        self,
        mode: str,
        src_type: str,
        src_file: str,
        dest: str,
        plaintext_text: str,
        pwd_bytes: bytearray,
        delete_source: bool
    ):
        error_title: Optional[str] = None
        error_msg: Optional[str] = None
        success_msg: Optional[str] = None
        decrypted_text_result: Optional[str] = None

        try:
            if mode == "encrypt":
                if src_type == "text":
                    encrypt_text_to_file(
                        text=plaintext_text,
                        output_path=dest,
                        password=pwd_bytes,
                        iterations=DEFAULT_ITERATIONS,
                        orig_filename="vault_secret.txt"
                    )
                    success_msg = f"Successfully created .kromium container file from text at:\n{dest}"
                else:
                    encrypt_file(
                        input_path=src_file,
                        output_path=dest,
                        password=pwd_bytes,
                        iterations=DEFAULT_ITERATIONS,
                        delete_source=delete_source
                    )
                    success_msg = f"Successfully encrypted file to:\n{dest}"
                    if delete_source:
                        success_msg += "\n\n✔ The original plaintext file was securely shredded and deleted."
            else:
                orig_name = decrypt_file(src_file, dest, pwd_bytes, delete_source=delete_source)
                success_msg = f"Successfully decrypted container to:\n{dest}"
                if orig_name:
                    success_msg += f"\n(Original container filename: {orig_name})"
                if delete_source:
                    success_msg += "\n\n✔ The encrypted .kromium file was securely shredded and deleted."
                
                # Attempt to preview text in UI viewer if valid UTF-8
                try:
                    with open(dest, "rb") as df:
                        raw_data = df.read(1024 * 1024)  # Preview up to 1 MB
                        decrypted_text_result = raw_data.decode("utf-8")
                except Exception:
                    pass
                except Exception:
                    pass
        except AuthenticationError:
            error_title = "Authentication Failed"
            error_msg = (
                "Decryption failed: Incorrect master password or the .kromium file has been altered/corrupted.\n\n"
                "The AES-GCM authentication tag check failed."
            )
        except InvalidHeaderError as e:
            error_title = "Invalid Kromium Container"
            error_msg = f"The selected file is not a valid .kromium container:\n{str(e)}"
        except UnsupportedVersionError as e:
            error_title = "Unsupported Container Version"
            error_msg = f"The file was created with an incompatible format version:\n{str(e)}"
        except CorruptedFileError as e:
            error_title = "Corrupted Container"
            error_msg = f"The .kromium container file is damaged or truncated:\n{str(e)}"
        except PermissionError:
            error_title = "Permission Denied"
            error_msg = "Access was denied by the operating system. Check file permissions."
        except Exception as e:
            error_title = "Operation Failed"
            error_msg = f"An unexpected error occurred: {str(e)}"
        finally:
            secure_wipe(pwd_bytes)
            self.after(0, self._on_worker_completed, error_title, error_msg, success_msg, decrypted_text_result, src_type)

    def _on_worker_completed(
        self,
        error_title: Optional[str],
        error_msg: Optional[str],
        success_msg: Optional[str],
        decrypted_text_result: Optional[str],
        src_type: str
    ):
        self.is_processing = False
        self.progress_bar.stop()
        self.action_btn.config(state="normal")

        self.pwd_entry.delete(0, tk.END)
        self.confirm_pwd_entry.delete(0, tk.END)
        self._on_password_changed()

        if error_title and error_msg:
            self.status_lbl.config(text=f"Error: {error_title}", fg=COLOR_DANGER)
            messagebox.showerror(error_title, error_msg)
        elif success_msg:
            self.status_lbl.config(text="Operation completed successfully.", fg=COLOR_KROMIUM_LIGHT)
            
            if self.current_mode.get() == "encrypt" and src_type == "text":
                self.text_editor.delete("1.0", tk.END)

            if decrypted_text_result is not None:
                self.decrypted_text_viewer.delete("1.0", tk.END)
                self.decrypted_text_viewer.insert("1.0", decrypted_text_result)

            messagebox.showinfo("Operation Succeeded", success_msg)
            self._inspect_selected_file()


def run_gui():
    app = KromiumApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
