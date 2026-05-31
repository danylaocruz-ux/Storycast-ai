import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../auth/providers/auth_provider.dart';
import '../../../data/services/api_service.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final user = auth.user;

    return Scaffold(
      appBar: AppBar(title: const Text('Configurações')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Perfil
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.surfaceCard,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    gradient: AppColors.gradientPrimary,
                    borderRadius: BorderRadius.circular(28),
                  ),
                  child: Center(
                    child: Text(
                      user?.initials ?? 'U',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                        fontSize: 20,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user?.name ?? '',
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      Text(
                        user?.email ?? '',
                        style: const TextStyle(fontSize: 13, color: AppColors.textSecondary),
                      ),
                      const SizedBox(height: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          user?.plan.toUpperCase() ?? 'FREE',
                          style: const TextStyle(
                            fontSize: 10,
                            color: AppColors.primary,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),
          const _SectionHeader('Conta'),
          _SettingsTile(
            icon: Icons.lock_outline,
            label: 'Alterar senha',
            onTap: () => _showPasswordDialog(context),
          ),

          const SizedBox(height: 16),
          const _SectionHeader('Vozes e Idioma'),
          _LanguageTile(),
          const SizedBox(height: 16),
          const _SectionHeader('Sobre'),
          _SettingsTile(
            icon: Icons.info_outline,
            label: 'StoryCast AI v1.0.0',
            onTap: null,
          ),
          _SettingsTile(
            icon: Icons.translate,
            label: 'edge-tts · PT-BR · EN · ES · FR',
            onTap: null,
            trailing: const SizedBox.shrink(),
          ),

          const SizedBox(height: 24),
          Container(
            decoration: BoxDecoration(
              color: AppColors.error.withOpacity(0.08),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.error.withOpacity(0.3)),
            ),
            child: ListTile(
              leading: const Icon(Icons.logout, color: AppColors.error),
              title: const Text('Sair da conta', style: TextStyle(color: AppColors.error)),
              onTap: () => _confirmLogout(context, ref),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showPasswordDialog(BuildContext context) async {
    final currentCtrl = TextEditingController();
    final newCtrl = TextEditingController();
    await showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surfaceCard,
        title: const Text('Alterar senha', style: TextStyle(color: AppColors.textPrimary)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: currentCtrl,
              obscureText: true,
              style: const TextStyle(color: AppColors.textPrimary),
              decoration: const InputDecoration(hintText: 'Senha atual'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: newCtrl,
              obscureText: true,
              style: const TextStyle(color: AppColors.textPrimary),
              decoration: const InputDecoration(hintText: 'Nova senha'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(_), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.pop(_), child: const Text('Salvar')),
        ],
      ),
    );
    currentCtrl.dispose();
    newCtrl.dispose();
  }

  Future<void> _confirmLogout(BuildContext context, WidgetRef ref) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surfaceCard,
        title: const Text('Sair', style: TextStyle(color: AppColors.textPrimary)),
        content: const Text(
          'Tem certeza que deseja sair?',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(_, false), child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(_, true),
            child: const Text('Sair', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
    if (confirm == true) {
      await ref.read(authProvider.notifier).logout();
      if (context.mounted) context.go('/login');
    }
  }
}


// ── Language preference tile ──────────────────────────────────────────────────

class _LanguageTile extends StatefulWidget {
  @override
  State<_LanguageTile> createState() => _LanguageTileState();
}

class _LanguageTileState extends State<_LanguageTile> {
  static const _key = 'preferred_voice_lang';
  static const _options = [
    {'code': 'all',   'label': 'Todos os idiomas', 'flag': '🌐'},
    {'code': 'pt-BR', 'label': 'Português (Brasil)', 'flag': '🇧🇷'},
    {'code': 'en',    'label': 'Inglês (EUA)', 'flag': '🇺🇸'},
    {'code': 'es',    'label': 'Espanhol', 'flag': '🇪🇸'},
    {'code': 'fr',    'label': 'Francês', 'flag': '🇫🇷'},
  ];

  String _current = 'pt-BR';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final val = await ApiService.instance.getPreference(_key);
    if (val != null && mounted) setState(() => _current = val);
  }

  String get _currentLabel =>
      _options.firstWhere((o) => o['code'] == _current,
          orElse: () => _options[1])['label']!;

  String get _currentFlag =>
      _options.firstWhere((o) => o['code'] == _current,
          orElse: () => _options[1])['flag']!;

  Future<void> _pick() async {
    final picked = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: AppColors.surfaceCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('Idioma padrão das vozes',
              style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600, fontSize: 16)),
          ),
          const Divider(height: 1, color: AppColors.border),
          ..._options.map((o) => ListTile(
            leading: Text(o['flag']!, style: const TextStyle(fontSize: 22)),
            title: Text(o['label']!, style: const TextStyle(color: AppColors.textPrimary)),
            trailing: o['code'] == _current
                ? const Icon(Icons.check, color: AppColors.primary)
                : null,
            onTap: () => Navigator.pop(_, o['code']),
          )),
          const SizedBox(height: 8),
        ],
      ),
    );
    if (picked != null) {
      await ApiService.instance.savePreference(_key, picked);
      if (mounted) setState(() => _current = picked);
    }
  }

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 8),
    decoration: BoxDecoration(
      color: AppColors.surfaceCard,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: AppColors.border),
    ),
    child: ListTile(
      leading: Text(_currentFlag, style: const TextStyle(fontSize: 22)),
      title: const Text('Idioma padrão das vozes',
        style: TextStyle(color: AppColors.textPrimary, fontSize: 14)),
      subtitle: Text(_currentLabel,
        style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
      trailing: const Icon(Icons.chevron_right, color: AppColors.textHint),
      onTap: _pick,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ),
  );
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(left: 4, bottom: 8),
        child: Text(
          title.toUpperCase(),
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w700,
            color: AppColors.textHint,
            letterSpacing: 1.2,
          ),
        ),
      );
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final Widget? trailing;

  const _SettingsTile({required this.icon, required this.label, required this.onTap, this.trailing});

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: AppColors.surfaceCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: ListTile(
          leading: Icon(icon, color: AppColors.textSecondary, size: 22),
          title: Text(label, style: const TextStyle(color: AppColors.textPrimary, fontSize: 14)),
          trailing: trailing ?? const Icon(Icons.chevron_right, color: AppColors.textHint),
          onTap: onTap,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
}
