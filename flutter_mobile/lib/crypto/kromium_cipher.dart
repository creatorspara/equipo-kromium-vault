// Equipo Kromium - Cryptographic Container Engine in Dart
// Format: .kromium Secure File Container (Specification v1)
// Cipher: AES-256-GCM AEAD, KDF: PBKDF2-HMAC-SHA256 (600,000 Rounds)

import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'package:cryptography/cryptography.dart';

class KromiumCryptoException implements Exception {
  final String message;
  KromiumCryptoException(this.message);
  @override
  String toString() => 'KromiumCryptoException: $message';
}

class KromiumCipher {
  static const List<int> magicHeader = [0x4B, 0x52, 0x4F, 0x4D, 0x49, 0x55, 0x4D, 0x00]; // "KROMIUM\0"
  static const int formatVersion = 1;
  static const int defaultIterations = 600000;
  static const int saltSize = 32;
  static const int nonceSize = 12;
  static const int tagSize = 16;

  /// Securely derives a 256-bit AES key using PBKDF2-HMAC-SHA256
  static Future<SecretKey> deriveKey(List<int> passwordBytes, List<int> salt, int iterations) async {
    final pbkdf2 = Pbkdf2(
      macAlgorithm: Hmac.sha256(),
      iterations: iterations,
      bits: 256,
    );
    return await pbkdf2.deriveKey(
      secretKey: SecretKey(passwordBytes),
      nonce: salt,
    );
  }

  /// Constructs the tamper-evident binary container header (Authenticated as AAD)
  static Uint8List buildHeader(List<int> salt, List<int> nonce, String originalFilename, int iterations) {
    final nameBytes = utf8.encode(originalFilename);
    final headerBuilder = BytesBuilder();
    
    // 1. Magic (8 bytes)
    headerBuilder.add(magicHeader);
    // 2. Version (1 byte)
    headerBuilder.addByte(formatVersion);
    // 3. Iterations (4 bytes big-endian uint32)
    final iterData = ByteData(4)..setUint32(0, iterations, Endian.big);
    headerBuilder.add(iterData.buffer.asUint8List());
    // 4. Salt (32 bytes)
    headerBuilder.add(salt);
    // 5. Nonce (12 bytes)
    headerBuilder.add(nonce);
    // 6. Name length (2 bytes uint16) & name bytes
    final nameLenData = ByteData(2)..setUint16(0, nameBytes.length, Endian.big);
    headerBuilder.add(nameLenData.buffer.asUint8List());
    headerBuilder.add(nameBytes);

    return headerBuilder.toBytes();
  }

  /// Encrypts plaintext bytes into a .kromium container binary payload
  static Future<Uint8List> encryptBytes({
    required List<int> plaintext,
    required String password,
    String originalFilename = "secret.txt",
    int iterations = defaultIterations,
  }) async {
    if (password.isEmpty) {
      throw KromiumCryptoException("Password cannot be empty.");
    }

    final random = Random.secure();
    final salt = List<int>.generate(saltSize, (_) => random.nextInt(256));
    final nonce = List<int>.generate(nonceSize, (_) => random.nextInt(256));

    final headerAad = buildHeader(salt, nonce, originalFilename, iterations);
    final passwordBytes = utf8.encode(password);

    final secretKey = await deriveKey(passwordBytes, salt, iterations);
    final algorithm = AesGcm.with256bits();

    // Encrypt with full header passed as Associated Data (AAD)
    final secretBox = await algorithm.encrypt(
      plaintext,
      secretKey: secretKey,
      nonce: nonce,
      aad: headerAad,
    );

    final output = BytesBuilder();
    output.add(headerAad);
    output.add(secretBox.cipherText);
    output.add(secretBox.mac.bytes); // 16-byte GCM authentication tag

    return output.toBytes();
  }

  /// Decrypts a .kromium container binary payload
  static Future<Map<String, dynamic>> decryptBytes({
    required Uint8List containerBytes,
    required String password,
  }) async {
    if (containerBytes.length < magicHeader.length + 1 + 4 + saltSize + nonceSize + 2 + tagSize) {
      throw KromiumCryptoException("Container is too short or corrupted.");
    }

    // Verify magic header
    for (int i = 0; i < magicHeader.length; i++) {
      if (containerBytes[i] != magicHeader[i]) {
        throw KromiumCryptoException("Invalid magic header: not a valid .kromium container.");
      }
    }

    int offset = magicHeader.length;
    final version = containerBytes[offset];
    offset += 1;
    if (version != formatVersion) {
      throw KromiumCryptoException("Unsupported container version: $version");
    }

    final iterData = ByteData.sublistView(containerBytes, offset, offset + 4);
    final iterations = iterData.getUint32(0, Endian.big);
    offset += 4;

    final salt = containerBytes.sublist(offset, offset + saltSize);
    offset += saltSize;

    final nonce = containerBytes.sublist(offset, offset + nonceSize);
    offset += nonceSize;

    final nameLenData = ByteData.sublistView(containerBytes, offset, offset + 2);
    final nameLen = nameLenData.getUint16(0, Endian.big);
    offset += 2;

    final nameBytes = containerBytes.sublist(offset, offset + nameLen);
    final originalFilename = utf8.decode(nameBytes, allowMalformed: true);
    offset += nameLen;

    final headerAad = containerBytes.sublist(0, offset);
    final payloadWithTag = containerBytes.sublist(offset);

    if (payloadWithTag.length < tagSize) {
      throw KromiumCryptoException("Encrypted payload is missing GCM tag.");
    }

    final cipherText = payloadWithTag.sublist(0, payloadWithTag.length - tagSize);
    final macBytes = payloadWithTag.sublist(payloadWithTag.length - tagSize);

    final passwordBytes = utf8.encode(password);
    final secretKey = await deriveKey(passwordBytes, salt, iterations);

    final algorithm = AesGcm.with256bits();
    try {
      final clearText = await algorithm.decrypt(
        SecretBox(cipherText, nonce: nonce, mac: Mac(macBytes)),
        secretKey: secretKey,
        aad: headerAad,
      );
      return {
        "plaintext": Uint8List.fromList(clearText),
        "originalFilename": originalFilename,
        "iterations": iterations,
      };
    } catch (_) {
      throw KromiumCryptoException("Authentication failed: Incorrect master password or file was tampered with.");
    }
  }

  /// Direct text encryption: automatically generates a .kromium container file
  static Future<void> encryptTextToFile({
    required String text,
    required String outputPath,
    required String password,
  }) async {
    final textBytes = utf8.encode(text);
    final containerBlob = await encryptBytes(
      plaintext: textBytes,
      password: password,
      originalFilename: "secret_vault.txt",
    );
    final file = File(outputPath);
    await file.writeAsBytes(containerBlob, flush: true);
  }

  /// Encrypts an existing file and automatically shreds & deletes the original
  static Future<void> encryptFileAutoDelete({
    required File inputFile,
    required String outputPath,
    required String password,
    bool deleteSource = true,
  }) async {
    if (!await inputFile.exists()) {
      throw KromiumCryptoException("Source file does not exist.");
    }
    final bytes = await inputFile.readAsBytes();
    final fileName = inputFile.uri.pathSegments.last;

    final containerBlob = await encryptBytes(
      plaintext: bytes,
      password: password,
      originalFilename: fileName,
    );

    final outFile = File(outputPath);
    await outFile.writeAsBytes(containerBlob, flush: true);

    if (deleteSource && await inputFile.exists()) {
      // Secure shred: overwrite with random bytes before delete
      final random = Random.secure();
      final shredData = List<int>.generate(bytes.length, (_) => random.nextInt(256));
      await inputFile.writeAsBytes(shredData, flush: true);
      await inputFile.delete();
    }
  }

  /// Decrypts a .kromium container file and optionally shreds & deletes the .kromium file
  static Future<String> decryptKromiumFile({
    required File inputFile,
    required String outputPath,
    required String password,
    bool deleteSource = true,
  }) async {
    final bytes = await inputFile.readAsBytes();
    final res = await decryptBytes(containerBytes: bytes, password: password);
    final plaintext = res["plaintext"] as Uint8List;
    final outFile = File(outputPath);
    await outFile.writeAsBytes(plaintext, flush: true);

    if (deleteSource && await inputFile.exists() && inputFile.path != outputPath) {
      final random = Random.secure();
      final shredData = List<int>.generate(bytes.length, (_) => random.nextInt(256));
      await inputFile.writeAsBytes(shredData, flush: true);
      await inputFile.delete();
    }
    return res["originalFilename"] as String? ?? "";
  }
}
