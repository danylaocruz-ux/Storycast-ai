import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/constants/app_constants.dart';
import '../../../data/models/user_model.dart';
import '../../../data/services/api_service.dart';

// ── Estado ────────────────────────────────────────────────────────────────────

class AuthState {
  final UserModel? user;
  final bool isLoading;
  final String? error;

  const AuthState({this.user, this.isLoading = false, this.error});

  bool get isAuthenticated => user != null;

  AuthState copyWith({UserModel? user, bool? isLoading, String? error, bool clearUser = false}) =>
      AuthState(
        user: clearUser ? null : (user ?? this.user),
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

// ── Notifier ──────────────────────────────────────────────────────────────────

class AuthNotifier extends StateNotifier<AuthState> {
  final ApiService _api = ApiService.instance;

  AuthNotifier() : super(const AuthState()) {
    _loadSavedUser();
  }

  Future<void> _loadSavedUser() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(AppConstants.userKey);
    if (raw != null) {
      try {
        final user = UserModel.fromJson(json.decode(raw) as Map<String, dynamic>);
        state = state.copyWith(user: user);
      } catch (_) {
        await prefs.remove(AppConstants.userKey);
      }
    }
  }

  Future<void> login(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final data = await _api.login(email, password);
      await _api.setToken(data['access_token'] as String);
      final user = UserModel.fromJson(data['user'] as Map<String, dynamic>);
      await _saveUser(user);
      state = state.copyWith(user: user, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: _parseError(e));
    }
  }

  Future<void> register(String name, String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final data = await _api.register(name, email, password);
      await _api.setToken(data['access_token'] as String);
      final user = UserModel.fromJson(data['user'] as Map<String, dynamic>);
      await _saveUser(user);
      state = state.copyWith(user: user, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: _parseError(e));
    }
  }

  Future<void> logout() async {
    await _api.clearToken();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(AppConstants.userKey);
    state = const AuthState();
  }

  void clearError() => state = state.copyWith(error: null);

  Future<void> _saveUser(UserModel user) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(AppConstants.userKey, json.encode(user.toJson()));
  }

  String _parseError(Object e) {
    final msg = e.toString();
    if (msg.contains('409')) return 'E-mail já cadastrado';
    if (msg.contains('401')) return 'E-mail ou senha inválidos';
    if (msg.contains('SocketException') || msg.contains('Connection refused')) {
      return 'Servidor indisponível. Verifique a conexão.';
    }
    return 'Erro inesperado. Tente novamente.';
  }
}

// ── Providers ─────────────────────────────────────────────────────────────────

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(),
);
