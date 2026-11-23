/**
 * ============================================================================
 * Equipo Kromium Vault - Client-Side Cryptographic Engine & Interactive Controller
 * 100% Zero-Knowledge Browser Execution using Web Crypto API
 * Format: .kromium Container Standard v1
 * Cipher: AES-256-GCM (NIST SP 800-38D) AEAD
 * KDF: PBKDF2-HMAC-SHA256 (600,000 Iterations, 32-Byte Salt)
 * Brand Kit: Equipo Kromium (Build · Open · Share)
 * ============================================================================
 */

(function () {
  'use strict';

  // Format Specification Constants
  const MAGIC_HEADER = new Uint8Array([0x4B, 0x52, 0x4F, 0x4D, 0x49, 0x55, 0x4D, 0x00]); // "KROMIUM\0"
  const FORMAT_VERSION = 1;
  const DEFAULT_ITERATIONS = 600000;
  const SALT_SIZE = 32;
  const NONCE_SIZE = 12;
  const TAG_SIZE = 16;

  // Release Asset Direct Links
  const ASSETS = {
    pc: "https://github.com/creatorspara/equipo-kromium-vault/releases/latest/download/EquipoKromium-Windows.exe",
    android: "https://github.com/creatorspara/equipo-kromium-vault/releases/latest/download/EquipoKromium-Android.apk"
  };

  // State
  let selectedFileToEncrypt = null;
  let selectedFileToDecrypt = null;
  let lastDecryptedResult = null;

  // -------------------------------------------------------------
  // Utility: Toast Messages
  // -------------------------------------------------------------
  function showToast(msg, duration = 3500) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = msg;
    toast.style.display = 'block';
    setTimeout(() => {
      toast.style.display = 'none';
    }, duration);
  }

  window.downloadAsset = function (platform) {
    const url = ASSETS[platform];
    const name = platform === 'pc' ? 'EquipoKromium-Windows.exe' : 'EquipoKromium-Android.apk';
    showToast(`⚡ Direct download started for ${name}...`);
    window.location.assign(url);
  };

  window.copyCommand = function (text) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('✔ PowerShell verification command copied to clipboard!');
    }).catch(() => {
      showToast('Command: ' + text);
    });
  };

  // -------------------------------------------------------------
  // PWA Service Worker Registration
  // -------------------------------------------------------------
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js').catch(err => {
        console.debug('ServiceWorker registration skipped:', err);
      });
    });
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

    header.set(MAGIC_HEADER, 0);
    header[8] = FORMAT_VERSION;
    view.setUint32(9, iterations, false);
    header.set(salt, 13);
    header.set(nonce, 13 + SALT_SIZE);
    view.setUint16(13 + SALT_SIZE + NONCE_SIZE, nameBytes.length, false);
    header.set(nameBytes, 13 + SALT_SIZE + NONCE_SIZE + 2);

    return header;
  }

  async function encryptToKromiumBlob(plaintextBytes, password, originalFilename) {
    const salt = window.crypto.getRandomValues(new Uint8Array(SALT_SIZE));
    const nonce = window.crypto.getRandomValues(new Uint8Array(NONCE_SIZE));
    const headerAad = buildContainerHeader(salt, nonce, originalFilename, DEFAULT_ITERATIONS);

    const aesKey = await deriveAesKey(password, salt, DEFAULT_ITERATIONS);

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
        iterations: iterations,
        saltHex: Array.from(salt).map(b => b.toString(16).padStart(2, '0')).join(''),
        nonceHex: Array.from(nonce).map(b => b.toString(16).padStart(2, '0')).join('')
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
  // UI & Event Bindings
  // -------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', () => {
    // Tab switching
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-tab');
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        const targetEl = document.getElementById(targetId);
        if (targetEl) targetEl.classList.add('active');
      });
    });

    // Toggle Password Visibility
    document.querySelectorAll('.toggle-pwd').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-target');
        const input = document.getElementById(targetId);
        if (!input) return;
        if (input.type === 'password') {
          input.type = 'text';
          btn.textContent = '🙈';
        } else {
          input.type = 'password';
          btn.textContent = '👁';
        }
      });
    });

    // Password Entropy Meter
    function bindEntropyMeter(inputId, fillId, labelId) {
      const input = document.getElementById(inputId);
      const fill = document.getElementById(fillId);
      const label = document.getElementById(labelId);
      if (!input || !fill || !label) return;

      input.addEventListener('input', () => {
        const pwd = input.value;
        if (!pwd) {
          label.textContent = "Score: 0 / 100";
          fill.style.width = "0%";
          fill.style.backgroundColor = "var(--danger)";
          return;
        }

        let score = 0;
        if (pwd.length >= 8) score += 25;
        if (pwd.length >= 14) score += 20;
        if (/[A-Z]/.test(pwd)) score += 15;
        if (/[a-z]/.test(pwd)) score += 15;
        if (/[0-9]/.test(pwd)) score += 15;
        if (/[^A-Za-z0-9]/.test(pwd)) score += 10;
        if (score > 100) score = 100;

        fill.style.width = score + "%";

        if (score <= 25) {
          fill.style.backgroundColor = "var(--danger)";
          label.textContent = `Weak (${score}/100) — Minimum 8 chars recommended`;
        } else if (score <= 60) {
          fill.style.backgroundColor = "var(--warning)";
          label.textContent = `Moderate (${score}/100)`;
        } else if (score <= 85) {
          fill.style.backgroundColor = "var(--secondary)";
          label.textContent = `Strong (${score}/100)`;
        } else {
          fill.style.backgroundColor = "var(--success)";
          label.textContent = `Hardened (${score}/100) — Equipo Kromium Standard`;
        }
      });
    }

    bindEntropyMeter('text-password', 'text-entropy-fill', 'text-entropy-label');
    bindEntropyMeter('file-password', 'file-entropy-fill', 'file-entropy-label');

    // -----------------------------------------------------------
    // Action 1: Text Encryption
    // -----------------------------------------------------------
    const btnEncryptText = document.getElementById('btn-encrypt-text');
    const textResultBox = document.getElementById('text-result-box');

    if (btnEncryptText) {
      btnEncryptText.addEventListener('click', async () => {
        const text = document.getElementById('text-input').value.trim();
        let filename = document.getElementById('text-filename').value.trim() || 'vault_secret.kromium';
        if (!filename.endsWith('.kromium')) filename += '.kromium';
        const pwd = document.getElementById('text-password').value;
        const confirm = document.getElementById('text-confirm').value;

        if (!text) {
          alert('Please enter sensitive credentials or text to encrypt.');
          return;
        }
        if (!pwd || pwd !== confirm) {
          alert('Password mismatch or empty.');
          return;
        }

        btnEncryptText.disabled = true;
        btnEncryptText.textContent = '🔒 Deriving Key (600k PBKDF2 Rounds)...';

        try {
          const enc = new TextEncoder();
          const plaintextBytes = enc.encode(text);
          const containerBytes = await encryptToKromiumBlob(plaintextBytes, pwd, filename.replace('.kromium', '.txt'));

          triggerDownload(containerBytes, filename);

          textResultBox.style.display = 'block';
          textResultBox.className = 'result-box success';
          textResultBox.innerHTML = `
            <div style="font-weight: 700; color: var(--success); font-size: 0.9rem;">
              ✔ Successfully encrypted and downloaded <code>${filename}</code>!
            </div>
            <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">
              Container Size: ${(containerBytes.length / 1024).toFixed(2)} KB &bull; Zero plaintext remains in browser memory.
            </p>
          `;
          showToast(`✔ Saved ${filename} to your Downloads!`);
        } catch (err) {
          textResultBox.style.display = 'block';
          textResultBox.className = 'result-box error';
          textResultBox.innerHTML = `<span style="color: var(--danger); font-weight: 700;">Error: ${err.message}</span>`;
        } finally {
          btnEncryptText.disabled = false;
          btnEncryptText.textContent = '🔒 Encrypt & Download .kromium File';
        }
      });
    }

    // -----------------------------------------------------------
    // Action 2: File Encryption
    // -----------------------------------------------------------
    const fileDropzone = document.getElementById('file-dropzone');
    const filePickerInput = document.getElementById('file-picker-input');
    const fileBadge = document.getElementById('file-selected-badge');
    const btnEncryptFile = document.getElementById('btn-encrypt-file');
    const fileResultBox = document.getElementById('file-result-box');

    if (fileDropzone && filePickerInput) {
      fileDropzone.addEventListener('click', () => filePickerInput.click());
      fileDropzone.addEventListener('dragover', (e) => { e.preventDefault(); fileDropzone.classList.add('dragover'); });
      fileDropzone.addEventListener('dragleave', () => fileDropzone.classList.remove('dragover'));
      fileDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        fileDropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
          handleFileSelected(e.dataTransfer.files[0]);
        }
      });
      filePickerInput.addEventListener('change', () => {
        if (filePickerInput.files.length) {
          handleFileSelected(filePickerInput.files[0]);
        }
      });
    }

    function handleFileSelected(file) {
      selectedFileToEncrypt = file;
      fileBadge.style.display = 'inline-block';
      fileBadge.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    }

    if (btnEncryptFile) {
      btnEncryptFile.addEventListener('click', async () => {
        if (!selectedFileToEncrypt) {
          alert('Please select or drop a target file first.');
          return;
        }
        const pwd = document.getElementById('file-password').value;
        const confirm = document.getElementById('file-confirm').value;

        if (!pwd || pwd !== confirm) {
          alert('Password mismatch or empty.');
          return;
        }

        btnEncryptFile.disabled = true;
        btnEncryptFile.textContent = '🔒 Encrypting File Container...';

        try {
          const buffer = await selectedFileToEncrypt.arrayBuffer();
          const plaintextBytes = new Uint8Array(buffer);
          const outFilename = `${selectedFileToEncrypt.name}.kromium`;

          const containerBytes = await encryptToKromiumBlob(plaintextBytes, pwd, selectedFileToEncrypt.name);
          triggerDownload(containerBytes, outFilename);

          fileResultBox.style.display = 'block';
          fileResultBox.className = 'result-box success';
          fileResultBox.innerHTML = `
            <div style="font-weight: 700; color: var(--success); font-size: 0.9rem;">
              ✔ Container created: <code>${outFilename}</code>
            </div>
            <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">
              Original Filename: <b>${selectedFileToEncrypt.name}</b> &bull; Encrypted Size: ${(containerBytes.length / 1024).toFixed(2)} KB
            </p>
          `;
          showToast(`✔ Saved ${outFilename} to Downloads!`);
        } catch (err) {
          fileResultBox.style.display = 'block';
          fileResultBox.className = 'result-box error';
          fileResultBox.innerHTML = `<span style="color: var(--danger); font-weight: 700;">Error: ${err.message}</span>`;
        } finally {
          btnEncryptFile.disabled = false;
          btnEncryptFile.textContent = '🔒 Encrypt File to .kromium';
        }
      });
    }

    // -----------------------------------------------------------
    // Action 3: Container Decryption
    // -----------------------------------------------------------
    const decryptDropzone = document.getElementById('decrypt-dropzone');
    const decryptFileInput = document.getElementById('decrypt-file-input');
    const decryptBadge = document.getElementById('decrypt-selected-badge');
    const btnDecrypt = document.getElementById('btn-decrypt-container');
    const decryptResultBox = document.getElementById('decrypt-result-box');

    if (decryptDropzone && decryptFileInput) {
      decryptDropzone.addEventListener('click', () => decryptFileInput.click());
      decryptDropzone.addEventListener('dragover', (e) => { e.preventDefault(); decryptDropzone.classList.add('dragover'); });
      decryptDropzone.addEventListener('dragleave', () => decryptDropzone.classList.remove('dragover'));
      decryptDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        decryptDropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
          handleDecryptFileSelected(e.dataTransfer.files[0]);
        }
      });
      decryptFileInput.addEventListener('change', () => {
        if (decryptFileInput.files.length) {
          handleDecryptFileSelected(decryptFileInput.files[0]);
        }
      });
    }

    function handleDecryptFileSelected(file) {
      selectedFileToDecrypt = file;
      decryptBadge.style.display = 'inline-block';
      decryptBadge.textContent = `Selected Container: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    }

    if (btnDecrypt) {
      btnDecrypt.addEventListener('click', async () => {
        if (!selectedFileToDecrypt) {
          alert('Please select or drop a .kromium container file.');
          return;
        }
        const pwd = document.getElementById('decrypt-password').value;
        if (!pwd) {
          alert('Please enter master password.');
          return;
        }

        btnDecrypt.disabled = true;
        btnDecrypt.textContent = '🔓 Verifying Tamper Authenticity & Decrypting...';

        try {
          const buffer = await selectedFileToDecrypt.arrayBuffer();
          const containerBytes = new Uint8Array(buffer);
          const result = await decryptKromiumBlob(containerBytes, pwd);
          lastDecryptedResult = result;

          let textPreview = '';
          try {
            const decoded = new TextDecoder('utf-8', { fatal: true }).decode(result.plaintext);
            textPreview = `
              <div style="margin-top: 1rem;">
                <label style="font-size: 0.75rem; font-weight: 700; color: var(--secondary);">Plaintext Preview:</label>
                <textarea readonly style="width: 100%; min-height: 80px; margin-top: 4px;">${decoded}</textarea>
              </div>
            `;
          } catch (_) {
            textPreview = `<p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 8px;">(Binary file restored: ${result.originalFilename})</p>`;
          }

          decryptResultBox.style.display = 'block';
          decryptResultBox.className = 'result-box success';
          decryptResultBox.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
              <span style="font-weight: 800; color: var(--success); font-size: 0.95rem;">
                ✔ Decryption Authenticated & Verified (NIST SP 800-38D AES-GCM)
              </span>
              <button id="btn-download-restored" class="btn-sm btn-primary-sm" style="font-size: 0.75rem;">
                📥 Download Restored File (${result.originalFilename})
              </button>
            </div>
            ${textPreview}
            <div class="meta-grid">
              <div class="meta-item"><div class="k">Filename</div><div class="v">${result.originalFilename}</div></div>
              <div class="meta-item"><div class="k">PBKDF2 Rounds</div><div class="v">${result.iterations.toLocaleString()}</div></div>
              <div class="meta-item"><div class="k">Salt (Hex)</div><div class="v">${result.saltHex.substring(0, 16)}...</div></div>
              <div class="meta-item"><div class="k">Nonce (Hex)</div><div class="v">${result.nonceHex}</div></div>
            </div>
          `;

          const btnDownloadRestored = document.getElementById('btn-download-restored');
          if (btnDownloadRestored) {
            btnDownloadRestored.addEventListener('click', () => {
              triggerDownload(result.plaintext, result.originalFilename);
              showToast(`Restored: ${result.originalFilename}`);
            });
          }

          showToast(`✔ Decrypted: ${result.originalFilename}`);
        } catch (err) {
          decryptResultBox.style.display = 'block';
          decryptResultBox.className = 'result-box error';
          decryptResultBox.innerHTML = `<span style="color: var(--danger); font-weight: 700;">${err.message}</span>`;
        } finally {
          btnDecrypt.disabled = false;
          btnDecrypt.textContent = '🔓 Decrypt & Authenticate Container';
        }
      });
    }
  });
})();
