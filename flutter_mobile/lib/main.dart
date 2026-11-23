// Equipo Kromium - Mobile Vault Application (Flutter / Dart)
// Brand Kit: Equipo Kromium (Build · Open · Share)
// Theme: Obsidian Base (#0A0A0F), Primary Purple (#6C4DFF), Lavender (#A78BFA)
// Public Storage Integration: /storage/emulated/0/Download/EquipoKromium/

import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';

import 'crypto/kromium_cipher.dart';
import 'theme/kromium_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const EquipoKromiumApp());
}

class EquipoKromiumApp extends StatelessWidget {
  const EquipoKromiumApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Equipo Kromium Vault',
      debugShowCheckedModeBanner: false,
      theme: KromiumTheme.darkTheme,
      home: const VaultHomeScreen(),
    );
  }
}

class VaultHomeScreen extends StatefulWidget {
  const VaultHomeScreen({super.key});

  @override
  State<VaultHomeScreen> createState() => _VaultHomeScreenState();
}

class _VaultHomeScreenState extends State<VaultHomeScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  static const MethodChannel _platform = MethodChannel('com.equipokromium.vault/platform');

  // Controllers for text encryption
  final TextEditingController _textInputController = TextEditingController();
  final TextEditingController _textFilenameController = TextEditingController();
  final TextEditingController _textPasswordController = TextEditingController();
  final TextEditingController _textConfirmPasswordController = TextEditingController();
  bool _textSaveToPublicDownloads = true;

  // Controllers for file encryption
  PlatformFile? _selectedFile;
  final TextEditingController _filePasswordController = TextEditingController();
  final TextEditingController _fileConfirmPasswordController = TextEditingController();
  bool _fileSaveToPublicDownloads = true;
  bool _autoDeleteSource = true;

  // Controllers for decryption
  PlatformFile? _selectedKromiumFile;
  final TextEditingController _decryptPasswordController = TextEditingController();
  bool _autoDeleteKromiumOnDecrypt = true;
  String _decryptedPlaintext = "";
  Map<String, dynamic>? _lastDecryptedMeta;
  Uint8List? _lastDecryptedRawBytes;

  bool _isProcessing = false;
  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _textInputController.dispose();
    _textFilenameController.dispose();
    _textPasswordController.dispose();
    _textConfirmPasswordController.dispose();
    _filePasswordController.dispose();
    _fileConfirmPasswordController.dispose();
    _decryptPasswordController.dispose();
    super.dispose();
  }

  // -------------------------------------------------------------
  // Storage & Android Public Downloads Integration
  // -------------------------------------------------------------
  Future<Directory> _resolveSaveDirectory({bool preferPublicDownloads = true}) async {
    if (Platform.isAndroid && preferPublicDownloads) {
      // 1. Direct standard public Downloads folder for Equipo Kromium
      final publicDownload = Directory('/storage/emulated/0/Download/EquipoKromium');
      try {
        if (!await publicDownload.exists()) {
          await publicDownload.create(recursive: true);
        }
        return publicDownload;
      } catch (_) {
        // 2. Fallback to /storage/emulated/0/Download
        final rootDownload = Directory('/storage/emulated/0/Download');
        try {
          if (await rootDownload.exists()) {
            return rootDownload;
          }
        } catch (_) {}
      }
      // 3. Fallback to external storage directory from path_provider
      try {
        final ext = await getExternalStorageDirectory();
        if (ext != null) {
          final sub = Directory('${ext.path}/EquipoKromium');
          if (!await sub.exists()) await sub.create(recursive: true);
          return sub;
        }
      } catch (_) {}
    }
    // Default to app documents directory
    return await getApplicationDocumentsDirectory();
  }

  Future<void> _notifyMediaScanner(String filePath) async {
    if (Platform.isAndroid) {
      try {
        await _platform.invokeMethod('scanFile', {'path': filePath});
      } catch (_) {}
    }
  }

  Future<void> _requestManageStoragePermission() async {
    if (Platform.isAndroid) {
      try {
        await _platform.invokeMethod('openManageStorageSettings');
      } catch (e) {
        _showFeedback("Could not open settings: $e", isError: true);
      }
    } else {
      _showFeedback("External storage management is native to Android.");
    }
  }

  void _showFeedback(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(isError ? Icons.error_outline : Icons.check_circle_outline, color: Colors.white, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(message, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500)),
            ),
          ],
        ),
        backgroundColor: isError ? KromiumTheme.danger : KromiumTheme.primaryPurple,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        margin: const EdgeInsets.all(12),
        duration: const Duration(seconds: 4),
      ),
    );
  }

  void _showSaveSuccessModal({
    required String title,
    required String savedPath,
    required int fileSize,
    String? originalDeletedNote,
  }) {
    if (!mounted) return;
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) {
        return Container(
          padding: const EdgeInsets.all(20),
          decoration: const BoxDecoration(
            color: KromiumTheme.cardBg,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
            border: Border(
              top: BorderSide(color: KromiumTheme.primaryPurple, width: 2),
              left: BorderSide(color: KromiumTheme.border),
              right: BorderSide(color: KromiumTheme.border),
            ),
          ),
          child: SafeArea(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: KromiumTheme.success.withOpacity(0.15),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.check_circle, color: KromiumTheme.success, size: 28),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                          const Text("Stored in Public Device Storage", style: TextStyle(fontSize: 12, color: KromiumTheme.lavender)),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, color: KromiumTheme.textMuted),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: KromiumTheme.inputBg,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: KromiumTheme.border),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text("Saved File Location:", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: KromiumTheme.lightAccent)),
                          Text("${(fileSize / 1024).toStringAsFixed(1)} KB", style: const TextStyle(fontSize: 11, color: KromiumTheme.textMuted)),
                        ],
                      ),
                      const SizedBox(height: 6),
                      SelectableText(
                        savedPath,
                        style: const TextStyle(fontSize: 12, color: KromiumTheme.textWhite, fontFamily: 'monospace'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: KromiumTheme.primaryPurple.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: KromiumTheme.primaryPurple.withOpacity(0.3)),
                  ),
                  child: Row(
                    children: const [
                      Icon(Icons.info_outline, color: KromiumTheme.lightAccent, size: 18),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          "Visible in your phone's 'Downloads' or 'Files' app under the 'EquipoKromium' folder.",
                          style: TextStyle(fontSize: 11, color: KromiumTheme.lightAccent),
                        ),
                      ),
                    ],
                  ),
                ),
                if (originalDeletedNote != null) ...[
                  const SizedBox(height: 8),
                  Text(originalDeletedNote, style: const TextStyle(fontSize: 11, color: Colors.amber, fontStyle: FontStyle.italic)),
                ],
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        icon: const Icon(Icons.copy, size: 16, color: KromiumTheme.lavender),
                        label: const Text("COPY PATH", style: TextStyle(color: KromiumTheme.lavender, fontSize: 12)),
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: savedPath));
                          _showFeedback("✔ File path copied to clipboard!");
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton(
                        child: const Text("DONE", style: TextStyle(fontSize: 12)),
                        onPressed: () => Navigator.pop(ctx),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // Password Strength Evaluator (0 to 1 score)
  double _calculateStrength(String password) {
    if (password.isEmpty) return 0.0;
    double score = 0.0;
    if (password.length >= 8) score += 0.25;
    if (password.length >= 14) score += 0.20;
    if (RegExp(r'[A-Z]').hasMatch(password)) score += 0.15;
    if (RegExp(r'[a-z]').hasMatch(password)) score += 0.15;
    if (RegExp(r'[0-9]').hasMatch(password)) score += 0.15;
    if (RegExp(r'[^A-Za-z0-9]').hasMatch(password)) score += 0.10;
    return score.clamp(0.0, 1.0);
  }

  Widget _buildPasswordStrengthBar(String password) {
    final strength = _calculateStrength(password);
    Color color;
    String label;
    if (strength <= 0.25) {
      color = KromiumTheme.danger;
      label = "Weak";
    } else if (strength <= 0.60) {
      color = Colors.amber;
      label = "Moderate";
    } else if (strength <= 0.85) {
      color = KromiumTheme.lavender;
      label = "Strong";
    } else {
      color = KromiumTheme.success;
      label = "Unbreakable";
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text("Entropy: $label", style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.bold)),
              Text("${(strength * 100).toInt()}%", style: TextStyle(fontSize: 11, color: color)),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: strength,
              backgroundColor: KromiumTheme.border,
              valueColor: AlwaysStoppedAnimation<Color>(color),
              minHeight: 4,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStorageBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: KromiumTheme.cardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: KromiumTheme.border),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: KromiumTheme.primaryPurple.withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.folder_special, color: KromiumTheme.lavender, size: 20),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text("Public Storage: Downloads/EquipoKromium", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                Text("Directly visible in Android Files & Downloads", style: TextStyle(fontSize: 10, color: KromiumTheme.textMuted)),
              ],
            ),
          ),
          TextButton.icon(
            icon: const Icon(Icons.security, size: 14, color: KromiumTheme.lightAccent),
            label: const Text("Access", style: TextStyle(fontSize: 11, color: KromiumTheme.lightAccent)),
            onPressed: _requestManageStoragePermission,
          ),
        ],
      ),
    );
  }

  int _getFileSize(PlatformFile file) {
    if (file.path != null) {
      try {
        return File(file.path!).lengthSync();
      } catch (_) {}
    }
    return 0;
  }

  // -------------------------------------------------------------
  // Action 1: Direct Text Encryption -> Save to Public Downloads
  // -------------------------------------------------------------
  Future<void> _encryptDirectText() async {
    final text = _textInputController.text.trim();
    final pwd = _textPasswordController.text;
    final confirm = _textConfirmPasswordController.text;

    if (text.isEmpty) {
      _showFeedback("Please enter sensitive text or credentials to encrypt.", isError: true);
      return;
    }
    if (pwd.isEmpty) {
      _showFeedback("Master password cannot be empty.", isError: true);
      return;
    }
    if (pwd != confirm) {
      _showFeedback("Master passwords do not match. Please re-enter.", isError: true);
      return;
    }

    setState(() => _isProcessing = true);
    try {
      final dir = await _resolveSaveDirectory(preferPublicDownloads: _textSaveToPublicDownloads);
      String rawFilename = _textFilenameController.text.trim();
      if (rawFilename.isEmpty) {
        final timestamp = DateTime.now().millisecondsSinceEpoch;
        rawFilename = "vault_note_$timestamp";
      }
      if (!rawFilename.endsWith(".kromium")) {
        rawFilename = "$rawFilename.kromium";
      }

      final outPath = "${dir.path}/$rawFilename";
      await KromiumCipher.encryptTextToFile(
        text: text,
        outputPath: outPath,
        password: pwd,
      );

      await _notifyMediaScanner(outPath);
      final savedSize = File(outPath).lengthSync();

      _textInputController.clear();
      _textFilenameController.clear();
      _textPasswordController.clear();
      _textConfirmPasswordController.clear();

      _showSaveSuccessModal(
        title: "Vault Container Created",
        savedPath: outPath,
        fileSize: savedSize,
      );
    } catch (e) {
      _showFeedback("Encryption error: $e", isError: true);
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  // -------------------------------------------------------------
  // Action 2: File Encryption -> Auto-delete source file
  // -------------------------------------------------------------
  Future<void> _pickSourceFile() async {
    try {
      final files = await FilePicker.pickFiles();
      if (files.isNotEmpty) {
        setState(() {
          _selectedFile = files.first;
        });
      }
    } catch (e) {
      _showFeedback("Error picking file: $e", isError: true);
    }
  }

  Future<void> _encryptFileAutoDelete() async {
    if (_selectedFile == null || _selectedFile!.path == null) {
      _showFeedback("Please select a target file from storage.", isError: true);
      return;
    }
    final pwd = _filePasswordController.text;
    final confirm = _fileConfirmPasswordController.text;

    if (pwd.isEmpty || pwd != confirm) {
      _showFeedback("Password mismatch or empty.", isError: true);
      return;
    }

    setState(() => _isProcessing = true);
    try {
      final srcFile = File(_selectedFile!.path!);
      final origName = _selectedFile!.name;
      
      String outPath;
      if (_fileSaveToPublicDownloads) {
        final dir = await _resolveSaveDirectory(preferPublicDownloads: true);
        outPath = "${dir.path}/$origName.kromium";
      } else {
        outPath = "${_selectedFile!.path!}.kromium";
      }

      await KromiumCipher.encryptFileAutoDelete(
        inputFile: srcFile,
        outputPath: outPath,
        password: pwd,
        deleteSource: _autoDeleteSource,
      );

      await _notifyMediaScanner(outPath);
      final savedSize = File(outPath).lengthSync();

      final shredNote = _autoDeleteSource
          ? "Original file '$origName' was securely overwritten and unlinked."
          : null;

      setState(() => _selectedFile = null);
      _filePasswordController.clear();
      _fileConfirmPasswordController.clear();

      _showSaveSuccessModal(
        title: "File Encrypted Successfully",
        savedPath: outPath,
        fileSize: savedSize,
        originalDeletedNote: shredNote,
      );
    } catch (e) {
      _showFeedback("File encryption error: $e", isError: true);
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  // -------------------------------------------------------------
  // Action 3: Decryption & Auto-Delete Container
  // -------------------------------------------------------------
  Future<void> _pickKromiumFile() async {
    try {
      final files = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['kromium', 'bin'],
      );
      if (files.isNotEmpty) {
        setState(() {
          _selectedKromiumFile = files.first;
          _decryptedPlaintext = "";
          _lastDecryptedMeta = null;
          _lastDecryptedRawBytes = null;
        });
      }
    } catch (e) {
      _showFeedback("Error picking .kromium file: $e", isError: true);
    }
  }

  Future<void> _decryptContainer() async {
    if (_selectedKromiumFile == null || _selectedKromiumFile!.path == null) {
      _showFeedback("Please select a .kromium container to decrypt.", isError: true);
      return;
    }
    final pwd = _decryptPasswordController.text;
    if (pwd.isEmpty) {
      _showFeedback("Please enter the master password.", isError: true);
      return;
    }

    setState(() => _isProcessing = true);
    try {
      final file = File(_selectedKromiumFile!.path!);
      final bytes = await file.readAsBytes();
      final result = await KromiumCipher.decryptBytes(containerBytes: bytes, password: pwd);

      final plaintextBytes = result["plaintext"] as Uint8List;
      final originalFilename = result["originalFilename"] as String? ?? "restored_file.bin";

      bool isText = false;
      String textContent = "";
      try {
        textContent = utf8.decode(plaintextBytes);
        isText = true;
      } catch (_) {
        isText = false;
      }

      setState(() {
        _lastDecryptedRawBytes = plaintextBytes;
        _lastDecryptedMeta = {
          "filename": originalFilename,
          "size": plaintextBytes.length,
          "iterations": result["iterations"] ?? 600000,
          "isText": isText,
        };
        if (isText) {
          _decryptedPlaintext = textContent;
        }
      });

      // Restore directly to public storage if binary
      if (!isText) {
        final dir = await _resolveSaveDirectory(preferPublicDownloads: true);
        final restoreFile = File("${dir.path}/$originalFilename");
        await restoreFile.writeAsBytes(plaintextBytes, flush: true);
        await _notifyMediaScanner(restoreFile.path);

        _showSaveSuccessModal(
          title: "Restored Binary File",
          savedPath: restoreFile.path,
          fileSize: plaintextBytes.length,
        );
      } else {
        _showFeedback("✔ Container decrypted! Preview and save options available below.");
      }

      // Securely shred container if auto-delete is enabled
      if (_autoDeleteKromiumOnDecrypt && await file.exists()) {
        final rand = List<int>.generate(bytes.length, (_) => 0);
        await file.writeAsBytes(rand, flush: true);
        await file.delete();
        setState(() => _selectedKromiumFile = null);
      }
    } catch (e) {
      _showFeedback("Decryption failed: $e", isError: true);
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  Future<void> _saveDecryptedTextToDownloads() async {
    if (_decryptedPlaintext.isEmpty && _lastDecryptedRawBytes == null) {
      _showFeedback("No decrypted data available to save.", isError: true);
      return;
    }

    try {
      final dir = await _resolveSaveDirectory(preferPublicDownloads: true);
      final filename = _lastDecryptedMeta?['filename'] ?? "decrypted_note.txt";
      final outPath = "${dir.path}/$filename";
      final outFile = File(outPath);

      if (_decryptedPlaintext.isNotEmpty) {
        await outFile.writeAsString(_decryptedPlaintext, flush: true);
      } else {
        await outFile.writeAsBytes(_lastDecryptedRawBytes!, flush: true);
      }

      await _notifyMediaScanner(outPath);
      final savedSize = outFile.lengthSync();

      _showSaveSuccessModal(
        title: "File Saved to Public Downloads",
        savedPath: outPath,
        fileSize: savedSize,
      );
    } catch (e) {
      _showFeedback("Error saving to downloads: $e", isError: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: KromiumTheme.baseDark,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(120),
        child: Container(
          decoration: const BoxDecoration(
            color: KromiumTheme.cardBg,
            border: Border(bottom: BorderSide(color: KromiumTheme.border, width: 1)),
          ),
          child: SafeArea(
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(7),
                        decoration: BoxDecoration(
                          color: const Color(0xFF201B3C),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: KromiumTheme.primaryPurple.withOpacity(0.4)),
                        ),
                        child: const Text("🛡️", style: TextStyle(fontSize: 18)),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Text("Equipo Kromium", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                                const SizedBox(width: 8),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: KromiumTheme.primaryPurple.withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(4),
                                    border: Border.all(color: KromiumTheme.primaryPurple.withOpacity(0.5)),
                                  ),
                                  child: const Text("AES-256-GCM", style: TextStyle(fontSize: 9, color: KromiumTheme.lightAccent, fontWeight: FontWeight.bold)),
                                ),
                              ],
                            ),
                            const Text("Build · Open · Share", style: TextStyle(fontSize: 11, color: KromiumTheme.lavender, fontWeight: FontWeight.w600)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                TabBar(
                  controller: _tabController,
                  indicatorColor: KromiumTheme.primaryPurple,
                  indicatorWeight: 3,
                  labelColor: KromiumTheme.lightAccent,
                  unselectedLabelColor: KromiumTheme.textMuted,
                  tabs: const [
                    Tab(icon: Icon(Icons.edit_note, size: 20), text: "Direct Text"),
                    Tab(icon: Icon(Icons.shield, size: 20), text: "File Vault"),
                    Tab(icon: Icon(Icons.lock_open, size: 20), text: "Decryptor"),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
      body: _isProcessing
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [
                  CircularProgressIndicator(color: KromiumTheme.primaryPurple),
                  SizedBox(height: 16),
                  Text("PBKDF2-HMAC-SHA256 (600,000 Rounds)...", style: TextStyle(fontSize: 12, color: KromiumTheme.lavender)),
                ],
              ),
            )
          : TabBarView(
              controller: _tabController,
              children: [
                _buildTextVaultTab(),
                _buildFileVaultTab(),
                _buildDecryptTab(),
              ],
            ),
    );
  }

  // TAB 1: Direct Text Vault
  Widget _buildTextVaultTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildStorageBanner(),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: KromiumTheme.cardBg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: KromiumTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text("Sensitive Text or Credentials", style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                    TextButton.icon(
                      icon: const Icon(Icons.paste, size: 14, color: KromiumTheme.lavender),
                      label: const Text("Paste", style: TextStyle(fontSize: 12, color: KromiumTheme.lavender)),
                      onPressed: () async {
                        final data = await Clipboard.getData(Clipboard.kTextPlain);
                        if (data != null && data.text != null) {
                          setState(() => _textInputController.text = data.text!);
                        }
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                TextField(
                  controller: _textInputController,
                  maxLines: 5,
                  style: const TextStyle(fontSize: 13, color: KromiumTheme.textWhite),
                  decoration: const InputDecoration(
                    hintText: "Enter passwords, API keys, secrets, or secure notes...\nA .kromium file will be created automatically.",
                  ),
                ),
                const SizedBox(height: 12),
                const Text("Container Filename (Optional)", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: KromiumTheme.textMuted)),
                const SizedBox(height: 6),
                TextField(
                  controller: _textFilenameController,
                  style: const TextStyle(fontSize: 13, color: KromiumTheme.textWhite),
                  decoration: const InputDecoration(
                    hintText: "e.g. master_credentials (defaults to timestamp)",
                    prefixIcon: Icon(Icons.description_outlined, size: 18, color: KromiumTheme.lavender),
                  ),
                ),
                const SizedBox(height: 10),
                CheckboxListTile(
                  value: _textSaveToPublicDownloads,
                  onChanged: (val) => setState(() => _textSaveToPublicDownloads = val ?? true),
                  title: const Text("📁 Save into Public Downloads (/Download/EquipoKromium)", style: TextStyle(fontSize: 12, color: KromiumTheme.lightAccent, fontWeight: FontWeight.w600)),
                  subtitle: const Text("Guarantees immediate visibility in phone's Files and Downloads apps", style: TextStyle(fontSize: 10, color: KromiumTheme.textMuted)),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: KromiumTheme.cardBg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: KromiumTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Master Password Protection", style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                const SizedBox(height: 8),
                TextField(
                  controller: _textPasswordController,
                  obscureText: _obscurePassword,
                  onChanged: (_) => setState(() {}),
                  decoration: InputDecoration(
                    hintText: "Enter Master Password",
                    suffixIcon: IconButton(
                      icon: Icon(_obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined, color: KromiumTheme.lavender, size: 18),
                      onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                    ),
                  ),
                ),
                if (_textPasswordController.text.isNotEmpty)
                  _buildPasswordStrengthBar(_textPasswordController.text),
                const SizedBox(height: 10),
                TextField(
                  controller: _textConfirmPasswordController,
                  obscureText: _obscurePassword,
                  decoration: const InputDecoration(hintText: "Confirm Master Password"),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            icon: const Icon(Icons.lock, size: 16),
            label: const Text("ENCRYPT & SAVE .KROMIUM FILE"),
            onPressed: _encryptDirectText,
          ),
        ],
      ),
    );
  }

  // TAB 2: File Vault
  Widget _buildFileVaultTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildStorageBanner(),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: KromiumTheme.cardBg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: KromiumTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Target File to Protect", style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                const SizedBox(height: 10),
                InkWell(
                  onTap: _pickSourceFile,
                  borderRadius: BorderRadius.circular(10),
                  child: Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: KromiumTheme.inputBg,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: _selectedFile != null ? KromiumTheme.primaryPurple : KromiumTheme.border),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          _selectedFile != null ? Icons.insert_drive_file : Icons.upload_file,
                          color: _selectedFile != null ? KromiumTheme.lightAccent : KromiumTheme.textMuted,
                          size: 24,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _selectedFile != null ? _selectedFile!.name : "Tap to browse & select file",
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.bold,
                                  color: _selectedFile != null ? KromiumTheme.textWhite : KromiumTheme.textMuted,
                                ),
                              ),
                              if (_selectedFile != null)
                                Text("${(_getFileSize(_selectedFile!) / 1024).toStringAsFixed(1)} KB", style: const TextStyle(fontSize: 11, color: KromiumTheme.lavender)),
                            ],
                          ),
                        ),
                        const Icon(Icons.folder_open, color: KromiumTheme.lavender, size: 20),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                CheckboxListTile(
                  value: _fileSaveToPublicDownloads,
                  onChanged: (val) => setState(() => _fileSaveToPublicDownloads = val ?? true),
                  title: const Text("📁 Save container into Public Downloads (/Download/EquipoKromium)", style: TextStyle(fontSize: 12, color: KromiumTheme.lightAccent, fontWeight: FontWeight.w600)),
                  subtitle: const Text("Ensures the resulting .kromium file is immediately findable", style: TextStyle(fontSize: 10, color: KromiumTheme.textMuted)),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                ),
                CheckboxListTile(
                  value: _autoDeleteSource,
                  onChanged: (val) => setState(() => _autoDeleteSource = val ?? true),
                  title: const Text("🗑️ Automatically securely shred & delete original file", style: TextStyle(fontSize: 12, color: KromiumTheme.lavender, fontWeight: FontWeight.bold)),
                  subtitle: const Text("Overwrites with cryptographically secure zero bytes before deleting", style: TextStyle(fontSize: 10, color: KromiumTheme.textMuted)),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: KromiumTheme.cardBg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: KromiumTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Master Password", style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                const SizedBox(height: 8),
                TextField(
                  controller: _filePasswordController,
                  obscureText: _obscurePassword,
                  onChanged: (_) => setState(() {}),
                  decoration: const InputDecoration(hintText: "Master Password"),
                ),
                if (_filePasswordController.text.isNotEmpty)
                  _buildPasswordStrengthBar(_filePasswordController.text),
                const SizedBox(height: 10),
                TextField(
                  controller: _fileConfirmPasswordController,
                  obscureText: _obscurePassword,
                  decoration: const InputDecoration(hintText: "Confirm Master Password"),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            icon: const Icon(Icons.lock, size: 16),
            label: const Text("ENCRYPT FILE & SAVE TO DOWNLOADS"),
            onPressed: _encryptFileAutoDelete,
          ),
        ],
      ),
    );
  }

  // TAB 3: Decryptor
  Widget _buildDecryptTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildStorageBanner(),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: KromiumTheme.cardBg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: KromiumTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Select .kromium Container", style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                const SizedBox(height: 10),
                InkWell(
                  onTap: _pickKromiumFile,
                  borderRadius: BorderRadius.circular(10),
                  child: Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: KromiumTheme.inputBg,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: _selectedKromiumFile != null ? KromiumTheme.primaryPurple : KromiumTheme.border),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          _selectedKromiumFile != null ? Icons.verified_user : Icons.file_open_outlined,
                          color: _selectedKromiumFile != null ? KromiumTheme.lightAccent : KromiumTheme.textMuted,
                          size: 24,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            _selectedKromiumFile != null ? _selectedKromiumFile!.name : "Select .kromium file to decrypt",
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              color: _selectedKromiumFile != null ? KromiumTheme.textWhite : KromiumTheme.textMuted,
                            ),
                          ),
                        ),
                        const Icon(Icons.folder_open, color: KromiumTheme.lavender, size: 20),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _decryptPasswordController,
                  obscureText: _obscurePassword,
                  decoration: InputDecoration(
                    hintText: "Enter Master Password",
                    suffixIcon: IconButton(
                      icon: Icon(_obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined, color: KromiumTheme.lavender, size: 18),
                      onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                CheckboxListTile(
                  value: _autoDeleteKromiumOnDecrypt,
                  onChanged: (val) => setState(() => _autoDeleteKromiumOnDecrypt = val ?? true),
                  title: const Text("🗑️ Delete & shred .kromium file after decrypting", style: TextStyle(fontSize: 12, color: KromiumTheme.lavender, fontWeight: FontWeight.bold)),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            icon: const Icon(Icons.lock_open, size: 16),
            label: const Text("DECRYPT .KROMIUM FILE"),
            onPressed: _decryptContainer,
          ),
          if (_lastDecryptedMeta != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: KromiumTheme.cardBg,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: KromiumTheme.success.withOpacity(0.5)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: const [
                          Icon(Icons.check_circle, color: KromiumTheme.success, size: 18),
                          SizedBox(width: 8),
                          Text("Decrypted Authenticated Data", style: TextStyle(fontWeight: FontWeight.bold, color: KromiumTheme.textWhite, fontSize: 13)),
                        ],
                      ),
                      IconButton(
                        icon: const Icon(Icons.copy, color: KromiumTheme.lavender, size: 18),
                        onPressed: () {
                          if (_decryptedPlaintext.isNotEmpty) {
                            Clipboard.setData(ClipboardData(text: _decryptedPlaintext));
                          }
                          _showFeedback("Copied to clipboard!");
                        },
                      ),
                    ],
                  ),
                  const Divider(color: KromiumTheme.border),
                  Text("Original Name: ${_lastDecryptedMeta!['filename']}", style: const TextStyle(fontSize: 11, color: KromiumTheme.lightAccent)),
                  Text("Payload Size: ${_lastDecryptedMeta!['size']} bytes", style: const TextStyle(fontSize: 11, color: KromiumTheme.textMuted)),
                  Text("PBKDF2 Iterations: ${_lastDecryptedMeta!['iterations']}", style: const TextStyle(fontSize: 11, color: KromiumTheme.textMuted)),
                  if (_decryptedPlaintext.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: KromiumTheme.inputBg,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: SelectableText(
                        _decryptedPlaintext,
                        style: const TextStyle(fontSize: 13, color: KromiumTheme.textWhite),
                      ),
                    ),
                  ],
                  const SizedBox(height: 14),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: KromiumTheme.success.withOpacity(0.2),
                      foregroundColor: KromiumTheme.textWhite,
                      side: const BorderSide(color: KromiumTheme.success),
                    ),
                    icon: const Icon(Icons.download, size: 16, color: KromiumTheme.success),
                    label: const Text("DEDICATED SAVE: EXPORT TO PUBLIC DOWNLOADS"),
                    onPressed: _saveDecryptedTextToDownloads,
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
