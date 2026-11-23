import 'package:flutter/material.dart';

class KromiumTheme {
  static const Color baseDark = Color(0xFF0A0A0F);
  static const Color cardBg = Color(0xFF12121A);
  static const Color inputBg = Color(0xFF0E0E16);
  static const Color border = Color(0xFF2A2640);

  static const Color primaryPurple = Color(0xFF6C4DFF);
  static const Color lavender = Color(0xFFA78BFA);
  static const Color lightAccent = Color(0xFFD1C4FF);
  static const Color textWhite = Color(0xFFF5F5F7);
  static const Color textMuted = Color(0xFF9D9AA8);

  static const Color success = Color(0xFF10B981);
  static const Color danger = Color(0xFFEF4444);

  static ThemeData get darkTheme {
    return ThemeData.dark().copyWith(
      scaffoldBackgroundColor: baseDark,
      primaryColor: primaryPurple,
      colorScheme: const ColorScheme.dark(
        primary: primaryPurple,
        secondary: lavender,
        surface: cardBg,
      ),
      textTheme: ThemeData.dark().textTheme.apply(
        fontFamily: 'Sora',
        bodyColor: textWhite,
        displayColor: textWhite,
      ),
      cardTheme: CardThemeData(
        color: cardBg,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: border, width: 1),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: inputBg,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: primaryPurple, width: 1.5),
        ),
        hintStyle: const TextStyle(color: textMuted, fontSize: 13),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryPurple,
          foregroundColor: textWhite,
          elevation: 0,
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, letterSpacing: 0.5),
        ),
      ),
    );
  }
}
