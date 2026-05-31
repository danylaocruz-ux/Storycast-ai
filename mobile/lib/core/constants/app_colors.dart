import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  // ── Primárias ──────────────────────────────────────────────────────────────
  static const primary = Color(0xFF7C3AED);       // Violeta
  static const primaryLight = Color(0xFF9F5CF7);
  static const primaryDark = Color(0xFF5B21B6);

  // ── Fundo ──────────────────────────────────────────────────────────────────
  static const background = Color(0xFF0A0A0F);
  static const surface = Color(0xFF13131A);
  static const surfaceVariant = Color(0xFF1C1C27);
  static const surfaceCard = Color(0xFF1E1E2E);

  // ── Texto ──────────────────────────────────────────────────────────────────
  static const textPrimary = Color(0xFFF1F1F5);
  static const textSecondary = Color(0xFF9999BB);
  static const textHint = Color(0xFF5A5A77);

  // ── Bordas ─────────────────────────────────────────────────────────────────
  static const border = Color(0xFF2A2A3E);

  // ── Status ─────────────────────────────────────────────────────────────────
  static const success = Color(0xFF10B981);
  static const error = Color(0xFFEF4444);
  static const warning = Color(0xFFF59E0B);
  static const info = Color(0xFF3B82F6);

  // ── Emoções (cores dos segmentos) ──────────────────────────────────────────
  static const emotionNeutral   = Color(0xFF6B7280);
  static const emotionHappy     = Color(0xFFF59E0B);
  static const emotionSad       = Color(0xFF3B82F6);
  static const emotionAngry     = Color(0xFFEF4444);
  static const emotionFearful   = Color(0xFF8B5CF6);
  static const emotionSurprised = Color(0xFF06B6D4);
  static const emotionRomantic  = Color(0xFFEC4899);
  static const emotionSuspense  = Color(0xFF374151);

  // ── Gradientes ─────────────────────────────────────────────────────────────
  static const gradientPrimary = LinearGradient(
    colors: [primary, Color(0xFF3B82F6)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const gradientBackground = LinearGradient(
    colors: [background, Color(0xFF0F0F1A)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  static Color emotion(String e) {
    const map = {
      'happy': emotionHappy,
      'sad': emotionSad,
      'angry': emotionAngry,
      'fearful': emotionFearful,
      'surprised': emotionSurprised,
      'romantic': emotionRomantic,
      'suspenseful': emotionSuspense,
    };
    return map[e] ?? emotionNeutral;
  }
}
