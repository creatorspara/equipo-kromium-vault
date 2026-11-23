// Equipo Kromium - Mobile Vault Application (Flutter / Dart)
// Brand Kit: Equipo Kromium (Build · Open · Share)

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

  // Controllers for text encryption
  final TextEditingController _textInputController = TextEditingController();
  final TextEditingController _textPasswordController = TextEditingController();
  final TextEditingController _textConfirmPasswordController = TextEditingController();

  // Controllers for file encryption
  PlatformFile? _selectedFile;
  final TextEditingController _filePasswordController = TextEditingController();
  final TextEditingController _fileConfirmPasswordController = TextEditingController();
  bool _autoDeleteSource = true;

  // Controllers for decryption
  PlatformFile? _selectedKromiumFile;
  final TextEditingController _decryptPasswordController = TextEditingController();
  String _decryptedPlaintext = "";

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
    _textPasswordController.dispose();
    _textConfirmPasswordController.dispose();
    _filePasswordController.dispose();
    _fileConfirmPasswordController.dispose();
    _decryptPasswordController.dispose();
    super.dispose();
  }

  void _showFeedback(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? KromiumTheme.danger : KromiumTheme.primaryPurple,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  // Action 1: Direct Text Encryption -> Auto-create .kromium container
  Future<void> _encryptDirectText() async {
    final text = _textInputController.text.trim();
    final pwd = _textPasswordController.text;
    final confirm = _textConfirmPasswordController.text;

    if (text.isEmpty) {
      _showFeedback("Please enter the sensitive text to encrypt.", isError: true);
      return;
    }
    if (pwd.isEmpty) {
      _showFeedback("Please enter a master password.", isError: true);
      return;
    }
    if (pwd != confirm) {
      _showFeedback("Passwords do not match.", isError: true);
      return;
    }

    setState(() => _isProcessing = true);
    try {
      final dir = await getApplicationDocumentsDirectory();
      final outPath = "${dir.path}/vault_text_${DateTime.now().millisecondsSinceEpoch}.kromium";
      await KromiumCipher.encryptTextToFile(
        text: text,
        outputPath: outPath,
        password: pwd,
      );

      _textInputController.clear();
      _textPasswordController.clear();
      _textConfirmPasswordController.clear();
      _showFeedback("✔ Successfully created .kromium container at:\n$outPath");
    } catch (e) {
      _showFeedback("Encryption failed: $e", isError: true);
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  // Action 2: File Encryption -> Auto-delete source file
  Future<void> _pickSourceFile() async {
    final result = await FilePicker.platform.pickFiles();
    if (result != null && result.files.isNotEmpty) {
      setState(() {
        _selectedFile = result.files.first;
      });
    }
  }

  Future<void> _encryptFileAutoDelete() async {
    if (_selectedFile == null || _selectedFile!.path == null) {
      _showFeedback("Please select a file to encrypt.", isError: true);
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
      final outPath = "${_selectedFile!.path!}.kromium";
      await KromiumCipher.encryptFileAutoDelete(
        inputFile: srcFile,
        outputPath: outPath,
        password: pwd,
        deleteSource: _autoDeleteSource,
      );

      final msg = _autoDeleteSource
          ? "✔ Encrypted to: $outPath\n(Original file was securely shredded & deleted)"
          : "✔ Encrypted to: $outPath";

      setState(() => _selectedFile = null);
      _filePasswordController.clear();
      _fileConfirmPasswordController.clear();
      _showFeedback(msg);
    } catch (e) {
      _showFeedback("File encryption error: $e", isError: true);
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  // Action 3: Decryption & In-App View
  Future<void> _pickKromiumFile() async {
    final result = await FilePicker.platform.pickFiles();
    if (result != null && result.files.isNotEmpty) {
      setState(() {
        _selectedKromiumFile = result.files.first;
      });
    }
  }

  Future<void> _decryptContainer() async {
    if (_selectedKromiumFile == null || _selectedKromiumFile!.path == null) {
      _showFeedback("Please select a .kromium file to decrypt.", isError: true);
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
      try {
        final decoded = utf8.decode(plaintextBytes);
        setState(() {
          _decryptedPlaintext = decoded;
        });
        _showFeedback("✔ Container decrypted successfully!");
      } catch (_) {
        // Binary file: restore to disk
        final outName = result["originalFilename"] ?? "restored_file.bin";
        final dir = await getApplicationDocumentsDirectory();
        final restoreFile = File("${dir.path}/$outName");
        await restoreFile.writeAsBytes(plaintextBytes);
        _showFeedback("✔ Binary file decrypted to: ${restoreFile.path}");
      }
    } catch (e) {
      _showFeedback("Decryption failed: $e", isError: true);
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: KromiumTheme.cardBg,
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF211A40),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Text("⚡", style: TextStyle(fontSize: 16)),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text("Equipo Kromium", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                Text("Build · Open · Share", style: TextStyle(fontSize: 10, color: KromiumTheme.lavender, fontWeight: FontWeight.w600)),
              ],
            ),
          ],
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: KromiumTheme.primaryPurple,
          labelColor: KromiumTheme.lightAccent,
          unselectedLabelColor: KromiumTheme.textMuted,
          tabs: const [
            Tab(text: "📝 Text Vault"),
            Tab(text: "📁 File Vault"),
            Tab(text: "🔓 Decrypt"),
          ],
        ),
      ),
      body: _isProcessing
          ? const Center(
              child: CircularProgressIndicator(color: KromiumTheme.primaryPurple),
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

  Widget _buildTextVaultTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Enter Sensitive Text / Passwords:", style: TextStyle(fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _textInputController,
                    maxLines: 5,
                    decoration: const InputDecoration(hintText: "Type or paste credentials, notes, recovery keys..."),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Master Access Password:", style: TextStyle(fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _textPasswordController,
                    obscureText: _obscurePassword,
                    decoration: InputDecoration(
                      hintText: "Master Password",
                      suffixIcon: IconButton(
                        icon: Icon(_obscurePassword ? Icons.visibility : Icons.visibility_off, color: KromiumTheme.lavender),
                        onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _textConfirmPasswordController,
                    obscureText: _obscurePassword,
                    decoration: const InputDecoration(hintText: "Confirm Master Password"),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _encryptDirectText,
            child: const Text("🔒 ENCRYPT TEXT & CREATE .KROMIUM FILE"),
          ),
        ],
      ),
    );
  }

  Widget _buildFileVaultTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Select Target File to Protect:", style: TextStyle(fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                  const SizedBox(height: 8),
                  ListTile(
                    tileColor: KromiumTheme.inputBg,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    title: Text(_selectedFile != null ? _selectedFile!.name : "No file selected", style: const TextStyle(fontSize: 13, color: KromiumTheme.textWhite)),
                    trailing: ElevatedButton(
                      onPressed: _pickSourceFile,
                      child: const Text("Browse"),
                    ),
                  ),
                  const SizedBox(height: 8),
                  CheckboxListTile(
                    value: _autoDeleteSource,
                    onChanged: (val) => setState(() => _autoDeleteSource = val ?? true),
                    title: const Text("Automatically securely shred & delete original file", style: TextStyle(fontSize: 12, color: KromiumTheme.lavender, fontWeight: FontWeight.bold)),
                    controlAffinity: ListTileControlAffinity.leading,
                    contentPadding: EdgeInsets.zero,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Master Password:", style: TextStyle(fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _filePasswordController,
                    obscureText: _obscurePassword,
                    decoration: const InputDecoration(hintText: "Master Password"),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _fileConfirmPasswordController,
                    obscureText: _obscurePassword,
                    decoration: const InputDecoration(hintText: "Confirm Master Password"),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _encryptFileAutoDelete,
            child: const Text("🔒 ENCRYPT FILE & AUTO-DELETE ORIGINAL"),
          ),
        ],
      ),
    );
  }

  Widget _buildDecryptTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Select .kromium Container:", style: TextStyle(fontWeight: FontWeight.bold, color: KromiumTheme.textWhite)),
                  const SizedBox(height: 8),
                  ListTile(
                    tileColor: KromiumTheme.inputBg,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    title: Text(_selectedKromiumFile != null ? _selectedKromiumFile!.name : "Select .kromium file", style: const TextStyle(fontSize: 13, color: KromiumTheme.textWhite)),
                    trailing: ElevatedButton(
                      onPressed: _pickKromiumFile,
                      child: const Text("Browse"),
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _decryptPasswordController,
                    obscureText: _obscurePassword,
                    decoration: const InputDecoration(hintText: "Master Password"),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _decryptContainer,
            child: const Text("🔓 DECRYPT .KROMIUM FILE"),
          ),
          if (_decryptedPlaintext.isNotEmpty) ...[
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text("Decrypted Content:", style: TextStyle(fontWeight: FontWeight.bold, color: KromiumTheme.lightAccent)),
                        IconButton(
                          icon: const Icon(Icons.copy, color: KromiumTheme.lavender, size: 20),
                          onPressed: () {
                            Clipboard.setData(ClipboardData(text: _decryptedPlaintext));
                            _showFeedback("Copied to clipboard!");
                          },
                        ),
                      ],
                    ),
                    const Divider(color: KromiumTheme.border),
                    SelectableText(
                      _decryptedPlaintext,
                      style: const TextStyle(fontFamily: 'Consolas', fontSize: 13, color: KromiumTheme.textWhite),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
