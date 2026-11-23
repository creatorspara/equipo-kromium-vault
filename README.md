# Equipo Kromium Vault (v2.0)
### Multi-Platform Authenticated Encryption Ecosystem (.EXE, .APK, Web App)
**Brand: Equipo Kromium &bull; Build &middot; Open &middot; Share**

---

## 1. Executive Summary & Brand Redesign

**Equipo Kromium Vault** has been redesigned from the ground up according to the **Equipo Kromium Brand Kit**:
- **Official Palette**:
  - Primary Brand Purple: `#6C4DFF`
  - Lavender Accent: `#A78BFA`
  - Light Purple Highlight: `#D1C4FF`
  - Deep Obsidian Base: `#0A0A0F`
  - Surface Cards: `#12121A` / `#161622` (Border: `#2A2640`)
  - Crisp Text: `#F5F5F7` (Secondary: `#9D9AA8`)
- **Typography**: **Sora** (Modern &bull; Clean &bull; Professional)
- **Tagline**: `Build · Open · Share`
- **Philosophy**: *"A student led developer team building open source software for a stronger, more open tech community."*
- **Enhanced Background**: High-definition rendering featuring atmospheric volumetric purple illumination, isometric cybernetic grid lines, and 3D geometric angled Kromium ribbon watermarks.

---

## 2. Multi-Platform Artifacts & Releases

All compiled standalone releases are ready in the `dist/` directory:

| Artifact | File Path | Platform | Description |
| :--- | :--- | :--- | :--- |
| **Standalone .EXE** | [`dist/EquipoKromium-Standalone.exe`](file:///C:/Users/vaish/.gemini/antigravity/scratch/kromium_vault/dist/EquipoKromium-Standalone.exe) | Windows 10/11 | Portable single-file executable with embedded brand icon, dark theme UI, and background worker threads. |
| **Release Folder .EXE** | [`dist/EquipoKromium/EquipoKromium.exe`](file:///C:/Users/vaish/.gemini/antigravity/scratch/kromium_vault/dist/EquipoKromium/EquipoKromium.exe) | Windows 10/11 | Unpacked distribution folder version for fast startup. |
| **Android .APK** | [`dist/EquipoKromium.apk`](file:///C:/Users/vaish/.gemini/antigravity/scratch/kromium_vault/dist/EquipoKromium.apk) | Android (minSdk 23+) | Release APK container package with manifest, DEX runtime, assets, and branding. |
| **Dart/Flutter Code**| [`flutter_mobile/`](file:///C:/Users/vaish/.gemini/antigravity/scratch/kromium_vault/flutter_mobile) | Android & iOS | Complete Flutter project (`lib/main.dart`, `kromium_cipher.dart`, `build_apk.bat`). |
| **Sub Web App** | [`web_app/index.html`](file:///C:/Users/vaish/.gemini/antigravity/scratch/kromium_vault/web_app/index.html) | Modern Web Browsers | Zero-install client-side web application using native Web Crypto API (AES-256-GCM + PBKDF2). |

---

## 3. Cryptographic Specification & Cross-Platform Protocol

The `.kromium` container is 100% interoperable across the Windows `.exe`, the Android `.apk`, and the Sub Web App:

| Parameter | Value | Standard / Defense |
| :--- | :--- | :--- |
| **Cipher** | **AES-256-GCM** | NIST SP 800-38D Authenticated Encryption with Associated Data |
| **Key Derivation** | **PBKDF2-HMAC-SHA256** | 600,000 iterations (OWASP recommendation) |
| **Salt** | 32 bytes (256-bit) | CSPRNG unique per file to defeat precomputation/rainbow tables |
| **Nonce / IV** | 12 bytes (96-bit) | CSPRNG unique per encryption to prevent IV reuse attacks |
| **Associated Data (AAD)**| Entire Container Header | Protects format version, iterations, salt, nonce, and original filename from tampering |
| **Auth Tag** | 16 bytes (128-bit) | Validates ciphertext and metadata integrity before releasing plaintext |
| **Source Erasure** | Auto-Shred & Delete | Plaintext files on disk are overwritten with random bytes and unlinked |

