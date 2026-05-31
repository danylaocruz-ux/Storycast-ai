import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../features/auth/providers/auth_provider.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/register_screen.dart';
import '../../features/home/screens/home_screen.dart';
import '../../features/library/screens/library_screen.dart';
import '../../features/upload/screens/upload_screen.dart';
import '../../features/processing/screens/processing_screen.dart';
import '../../features/characters/screens/characters_screen.dart';
import '../../features/player/screens/player_screen.dart';
import '../../features/settings/screens/settings_screen.dart';
import '../../shared/widgets/main_scaffold.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: authState.isAuthenticated ? '/home' : '/login',
    redirect: (context, state) {
      final isAuth = authState.isAuthenticated;
      final isOnAuth = state.matchedLocation == '/login' || state.matchedLocation == '/register';

      if (!isAuth && !isOnAuth) return '/login';
      if (isAuth && isOnAuth) return '/home';
      return null;
    },
    routes: [
      // ── Auth ────────────────────────────────────────────────────────────
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),

      // ── App principal com bottom navigation ─────────────────────────────
      ShellRoute(
        builder: (context, state, child) => MainScaffold(child: child),
        routes: [
          GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
          GoRoute(path: '/library', builder: (_, __) => const LibraryScreen()),
          GoRoute(path: '/upload', builder: (_, __) => const UploadScreen()),
          GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
        ],
      ),

      // ── Telas full-screen ────────────────────────────────────────────────
      GoRoute(
        path: '/processing/:bookId',
        builder: (_, state) => ProcessingScreen(
          bookId: int.parse(state.pathParameters['bookId']!),
        ),
      ),
      GoRoute(
        path: '/characters/:bookId',
        builder: (_, state) => CharactersScreen(
          bookId: int.parse(state.pathParameters['bookId']!),
        ),
      ),
      GoRoute(
        path: '/player/:bookId',
        builder: (_, state) => PlayerScreen(
          bookId: int.parse(state.pathParameters['bookId']!),
        ),
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Text(
          'Página não encontrada: ${state.uri}',
          style: const TextStyle(color: Colors.white),
        ),
      ),
    ),
  );
});
