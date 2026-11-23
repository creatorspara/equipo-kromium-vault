/**
 * Equipo Kromium Vault - Sub Web Application
 * 100% Client-Side Cryptographic Engine using Web Crypto API
 * Format: .kromium v1 container (AES-256-GCM + PBKDF2-HMAC-SHA256 600k rounds + AAD)
 */

(function () {
  'use strict';

  // Constants
  const MAGIC_HEADER = new Uint8Array([0x4B, 0x52, 0x4F, 0x4D, 0x49, 0x55, 0x4D, 0x00]); // "KROMIUM\0"
  const FORMAT_VERSION = 1;
  const DEFAULT_ITERATIONS = 600000;
  const SALT_SIZE = 32;
  const NONCE_SIZE = 12;
  const TAG_SIZE = 16;

  // DOM Elements
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  const statusMsg = document.getElementById('status-message');

  let selectedFileToEncrypt = null;
  let selectedFileToDecrypt = null;
  let lastDecryptedBlob = null;
  let lastDecryptedFilename = "restored_file.bin";

  // Tab switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(targetId).classList.add('active');
      setStatus("Switched mode: " + btn.innerText.trim());
    });
  });

  // Toggle password visibility
  document.querySelectorAll('.toggle-pwd').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (input.type === 'password') {
        input.type = 'text';
        btn.innerText = '🙈';
      } else {
        input.type = 'password';
        btn.innerText = '👁';
      }
    });
  });

  // Password entropy meter
  const textPwdInput = document.getElementById('text-password');
  const textStrengthLabel = document.getElementById('text-strength-label');
  const textEntropyFill = document.getElementById('text-entropy-fill');

  textPwdInput.addEventListener('input', () => {
    const pwd = textPwdInput.value;
    if (!pwd) {
      textStrengthLabel.innerText = "Empty";
      textEntropyFill.style.width = "0%";
      textEntropyFill.style.background = "var(--danger)";
      return;
    }

    let score = 0;
    if (pwd.length >= 8) score++;
    if (pwd.length >= 12) score++;
    if (pwd.length >= 16) score++;
    if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) score++;
    if (/\d/.test(pwd)) score++;
    if (/[^a-zA-Z0-9]/.test(pwd)) score++;

    if (score <= 2) {
      textStrengthLabel.innerText = "Weak (12+ mixed chars recommended)";
      textEntropyFill.style.width = "25%";
      textEntropyFill.style.background = "var(--danger)";
    } else if (score <= 4) {
      textStrengthLabel.innerText = "Moderate";
      textEntropyFill.style.width = "55%";
      textEntropyFill.style.background = "var(--warning)";
    } else if (score <= 5) {
      textStrengthLabel.innerText = "Strong";
      textEntropyFill.style.width = "80%";
      textEntropyFill.style.background = "var(--lavender)";
    } else {
      textStrengthLabel.innerText = "Hardened (Equipo Kromium)";
      textEntropyFill.style.width = "100%";
      textEntropyFill.style.background = "var(--light-accent)";
    }
  });

  function setStatus(msg, isError = false) {
    statusMsg.innerText = msg;
    statusMsg.style.color = isError ? 'var(--danger)' : 'var(--text-white)';
  }

  // -------------------------------------------------------------
  // Cryptographic Engine Core (Web Crypto API)
  // -------------------------------------------------------------
  async function deriveAesKey(password, salt, iterations) {
    const enc = new TextEncoder();
    const keyMaterial = await window.crypto.subtle.importKey(
      "raw",
      enc.encode(password),
      { name: "PBKDF2" },
      false,
      ["deriveKey"]
    );

    return await window.crypto.subtle.deriveKey(
      {
        name: "PBKDF2",
        salt: salt,
        iterations: iterations,
        hash: "SHA-256"
      },
      keyMaterial,
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"]
    );
  }

  function buildContainerHeader(salt, nonce, origFilename, iterations = DEFAULT_ITERATIONS) {
    const enc = new TextEncoder();
    const nameBytes = enc.encode(origFilename);
    const headerLen = 8 + 1 + 4 + SALT_SIZE + NONCE_SIZE + 2 + nameBytes.length;
    const header = new Uint8Array(headerLen);
    const view = new DataView(header.buffer);

    // Magic
    header.set(MAGIC_HEADER, 0);
    // Version
    header[8] = FORMAT_VERSION;
    // Iterations (uint32 big-endian)
    view.setUint32(9, iterations, false);
    // Salt
    header.set(salt, 13);
    // Nonce
    header.set(nonce, 13 + SALT_SIZE);
    // Name Length (uint16 big-endian)
    view.setUint16(13 + SALT_SIZE + NONCE_SIZE, nameBytes.length, false);
    // Name Bytes
    header.set(nameBytes, 13 + SALT_SIZE + NONCE_SIZE + 2);

    return header;
  }

  async function encryptToKromiumBlob(plaintextBytes, password, originalFilename) {
    const salt = window.crypto.getRandomValues(new Uint8Array(SALT_SIZE));
    const nonce = window.crypto.getRandomValues(new Uint8Array(NONCE_SIZE));
    const headerAad = buildContainerHeader(salt, nonce, originalFilename, DEFAULT_ITERATIONS);

    const aesKey = await deriveAesKey(password, salt, DEFAULT_ITERATIONS);

    // Encrypt with full header as Associated Data (AAD)
    const ciphertextBuffer = await window.crypto.subtle.encrypt(
      {
        name: "AES-GCM",
        iv: nonce,
        additionalData: headerAad
      },
      aesKey,
      plaintextBytes
    );

    const cipherBytes = new Uint8Array(ciphertextBuffer);
    const totalContainer = new Uint8Array(headerAad.length + cipherBytes.length);
    totalContainer.set(headerAad, 0);
    totalContainer.set(cipherBytes, headerAad.length);

    return totalContainer;
  }

  async function decryptKromiumBlob(containerBytes, password) {
    if (containerBytes.length < 59 + TAG_SIZE) {
      throw new Error("File is too small to be a valid .kromium container.");
    }

    // Verify magic
    for (let i = 0; i < MAGIC_HEADER.length; i++) {
      if (containerBytes[i] !== MAGIC_HEADER[i]) {
        throw new Error("Invalid magic bytes. Not a valid .kromium file.");
      }
    }

    const version = containerBytes[8];
    if (version !== FORMAT_VERSION) {
      throw new Error(`Unsupported container version: ${version}`);
    }

    const view = new DataView(containerBytes.buffer, containerBytes.byteOffset, containerBytes.byteLength);
    const iterations = view.getUint32(9, false);

    const salt = containerBytes.slice(13, 13 + SALT_SIZE);
    const nonce = containerBytes.slice(13 + SALT_SIZE, 13 + SALT_SIZE + NONCE_SIZE);

    const nameLen = view.getUint16(13 + SALT_SIZE + NONCE_SIZE, false);
    const nameOffset = 13 + SALT_SIZE + NONCE_SIZE + 2;
    const nameBytes = containerBytes.slice(nameOffset, nameOffset + nameLen);
    const origFilename = new TextDecoder().decode(nameBytes);

    const headerAad = containerBytes.slice(0, nameOffset + nameLen);
    const ciphertextWithTag = containerBytes.slice(nameOffset + nameLen);

    if (ciphertextWithTag.length < TAG_SIZE) {
      throw new Error("Container missing GCM authentication tag.");
    }

    const aesKey = await deriveAesKey(password, salt, iterations);

    try {
      const plaintextBuffer = await window.crypto.subtle.decrypt(
        {
          name: "AES-GCM",
          iv: nonce,
          additionalData: headerAad
        },
        aesKey,
        ciphertextWithTag
      );

      return {
        plaintext: new Uint8Array(plaintextBuffer),
        originalFilename: origFilename,
        iterations: iterations
      };
    } catch (err) {
      throw new Error("Authentication failed: Incorrect password or corrupted/tampered file.");
    }
  }

  function triggerDownload(blobBytes, filename) {
    const blob = new Blob([blobBytes], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 1500);
  }

  // -------------------------------------------------------------
  // TAB 1: Direct Text Encryption
  // -------------------------------------------------------------
  document.getElementById('btn-encrypt-text').addEventListener('click', async () => {
    const text = document.getElementById('text-input').value.trim();
    let filename = document.getElementById('text-filename').value.trim() || 'vault_secret.kromium';
    if (!filename.toLowerCase().endsWith('.kromium')) filename += '.kromium';

    const pwd = document.getElementById('text-password').value;
    const confirm = document.getElementById('text-confirm-password').value;

    if (!text) {
      alert("Please enter sensitive text or passwords to encrypt.");
      return;
    }
    if (!pwd) {
      alert("Please enter a master password.");
      return;
    }
    if (pwd !== confirm) {
      alert("Passwords do not match.");
      return;
    }

    setStatus("Deriving key (600,000 PBKDF2 rounds) & encrypting text...");
    try {
      const enc = new TextEncoder();
      const plaintextBytes = enc.encode(text);
      const containerBytes = await encryptToKromiumBlob(plaintextBytes, pwd, "secret_vault.txt");

      triggerDownload(containerBytes, filename);
      document.getElementById('text-input').value = "";
      document.getElementById('text-password').value = "";
      document.getElementById('text-confirm-password').value = "";
      textEntropyFill.style.width = "0%";
      textStrengthLabel.innerText = "Empty";

      setStatus(`✔ Success! Automatically created and downloaded container: ${filename}`);
    } catch (err) {
      setStatus(`Encryption failed: ${err.message}`, true);
      alert(err.message);
    }
  });

  // -------------------------------------------------------------
  // TAB 2: File Encryption
  // -------------------------------------------------------------
  const fileDropZone = document.getElementById('file-drop-zone');
  const fileInput = document.getElementById('file-input');
  const selectedFileBadge = document.getElementById('selected-file-badge');

  fileDropZone.addEventListener('click', () => fileInput.click());
  fileDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileDropZone.classList.add('drag-over');
  });
  fileDropZone.addEventListener('dragleave', () => fileDropZone.classList.remove('drag-over'));
  fileDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    fileDropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleFileSelected(fileInput.files[0]);
    }
  });

  function handleFileSelected(file) {
    selectedFileToEncrypt = file;
    selectedFileBadge.style.display = 'inline-block';
    selectedFileBadge.innerText = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    setStatus(`Selected source file: ${file.name}`);
  }

  document.getElementById('btn-encrypt-file').addEventListener('click', async () => {
    if (!selectedFileToEncrypt) {
      alert("Please select a file to encrypt first.");
      return;
    }
    const pwd = document.getElementById('file-password').value;
    const confirm = document.getElementById('file-confirm-password').value;

    if (!pwd || pwd !== confirm) {
      alert("Password is empty or passwords do not match.");
      return;
    }

    setStatus(`Encrypting ${selectedFileToEncrypt.name} (600,000 PBKDF2 rounds)...`);
    try {
      const buffer = await selectedFileToEncrypt.arrayBuffer();
      const plaintextBytes = new Uint8Array(buffer);
      const containerBytes = await encryptToKromiumBlob(plaintextBytes, pwd, selectedFileToEncrypt.name);

      const outName = selectedFileToEncrypt.name + ".kromium";
      triggerDownload(containerBytes, outName);

      document.getElementById('file-password').value = "";
      document.getElementById('file-confirm-password').value = "";
      setStatus(`✔ Success! File encrypted to ${outName}`);
    } catch (err) {
      setStatus(`File encryption error: ${err.message}`, true);
      alert(err.message);
    }
  });

  // -------------------------------------------------------------
  // TAB 3: Decrypt Container
  // -------------------------------------------------------------
  const decryptDropZone = document.getElementById('decrypt-drop-zone');
  const decryptFileInput = document.getElementById('decrypt-file-input');
  const decryptFileBadge = document.getElementById('decrypt-file-badge');
  const metaBanner = document.getElementById('container-meta-banner');
  const decryptedResultBox = document.getElementById('decrypted-result-box');
  const decryptedTextView = document.getElementById('decrypted-text-view');

  decryptDropZone.addEventListener('click', () => decryptFileInput.click());
  decryptDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    decryptDropZone.classList.add('drag-over');
  });
  decryptDropZone.addEventListener('dragleave', () => decryptDropZone.classList.remove('drag-over'));
  decryptDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    decryptDropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
      handleDecryptFileSelected(e.dataTransfer.files[0]);
    }
  });

  decryptFileInput.addEventListener('change', () => {
    if (decryptFileInput.files.length > 0) {
      handleDecryptFileSelected(decryptFileInput.files[0]);
    }
  });

  async function handleDecryptFileSelected(file) {
    selectedFileToDecrypt = file;
    decryptFileBadge.style.display = 'inline-block';
    decryptFileBadge.innerText = `Container: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;

    // Try peek header
    try {
      const slice = file.slice(0, 500);
      const buf = await slice.arrayBuffer();
      const bytes = new Uint8Array(buf);
      if (bytes.length > 59 && bytes[0] === 0x4B && bytes[1] === 0x52) {
        metaBanner.style.display = 'block';
        const view = new DataView(bytes.buffer);
        const iters = view.getUint32(9, false);
        const nameLen = view.getUint16(13 + SALT_SIZE + NONCE_SIZE, false);
        const nameOffset = 13 + SALT_SIZE + NONCE_SIZE + 2;
        const nameBytes = bytes.slice(nameOffset, nameOffset + nameLen);
        const origName = new TextDecoder().decode(nameBytes);

        document.getElementById('meta-version').innerText = `Format: v${bytes[8]}`;
        document.getElementById('meta-iters').innerText = `Rounds: ${iters.toLocaleString()}`;
        document.getElementById('meta-orig-name').innerText = `Embedded Original Name: ${origName || 'Unknown'}`;
      }
    } catch (_) {}
    setStatus(`Selected .kromium container: ${file.name}`);
  }

  document.getElementById('btn-decrypt-execute').addEventListener('click', async () => {
    if (!selectedFileToDecrypt) {
      alert("Please select a .kromium file to decrypt.");
      return;
    }
    const pwd = document.getElementById('decrypt-password').value;
    if (!pwd) {
      alert("Please enter the master password.");
      return;
    }

    setStatus("Verifying AEAD tag and decrypting container...");
    try {
      const buf = await selectedFileToDecrypt.arrayBuffer();
      const containerBytes = new Uint8Array(buf);
      const res = await decryptKromiumBlob(containerBytes, pwd);

      lastDecryptedBlob = res.plaintext;
      lastDecryptedFilename = res.originalFilename || (selectedFileToDecrypt.name.endsWith('.kromium') ? selectedFileToDecrypt.name.slice(0, -8) : 'restored.bin');

      // Attempt text decode
      try {
        const text = new TextDecoder('utf-8', { fatal: true }).decode(res.plaintext);
        decryptedResultBox.style.display = 'block';
        decryptedTextView.value = text;
        setStatus(`✔ Unlocked successfully! Content previewed below.`);
      } catch (_) {
        decryptedResultBox.style.display = 'block';
        decryptedTextView.value = `[Binary File Content: ${res.plaintext.length} bytes]\nOriginal Filename: ${lastDecryptedFilename}\nClick "Download Restored File" below to save.`;
        setStatus(`✔ Unlocked binary file (${res.plaintext.length} bytes). Ready to download.`);
      }
    } catch (err) {
      setStatus(`Decryption error: ${err.message}`, true);
      alert(err.message);
    }
  });

  document.getElementById('btn-copy-result').addEventListener('click', () => {
    if (decryptedTextView.value) {
      navigator.clipboard.writeText(decryptedTextView.value).then(() => {
        setStatus("✔ Decrypted text copied to clipboard!");
      });
    }
  });

  document.getElementById('btn-download-result').addEventListener('click', () => {
    if (lastDecryptedBlob) {
      triggerDownload(lastDecryptedBlob, lastDecryptedFilename);
    }
  });

})();
