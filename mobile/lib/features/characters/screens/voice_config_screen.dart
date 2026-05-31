import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/character_model.dart';
import '../../../data/models/voice_model.dart';
import '../../../data/services/api_service.dart';

class VoiceConfigScreen extends ConsumerStatefulWidget {
  final int bookId;
  const VoiceConfigScreen({super.key, required this.bookId});

  @override
  ConsumerState<VoiceConfigScreen> createState() => _VoiceConfigScreenState();
}

class _VoiceConfigScreenState extends ConsumerState<VoiceConfigScreen>
    with SingleTickerProviderStateMixin {
  List<CharacterModel> _characters = [];
  List<VoiceModel> _voices = [];
  final Map<int, VoiceModel> _pendingChanges = {};
  bool _isLoading = true;
  bool _isSaving = false;
  bool _isRegenerating = false;
  String? _error;
  late TabController _tabController;

  static const _langs = ['Todos', 'PT-BR', 'EN', 'ES', 'FR'];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _langs.length, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait([
        ApiService.instance.getCharacters(widget.bookId),
        ApiService.instance.getAvailableVoices(),
      ]);
      setState(() {
        _characters = (results[0] as List)
            .map((e) => CharacterModel.fromJson(e as Map<String, dynamic>))
            .toList();
        _voices = (results[1] as List)
            .map((e) => VoiceModel.fromJson(e as Map<String, dynamic>))
            .toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() { _error = e.toString(); _isLoading = false; });
    }
  }

  List<VoiceModel> _filteredVoices(String lang) {
    if (lang == 'Todos') return _voices;
    if (lang == 'PT-BR') return _voices.where((v) => v.locale.startsWith('pt-BR')).toList();
    if (lang == 'EN') return _voices.where((v) => v.locale.startsWith('en-')).toList();
    if (lang == 'ES') return _voices.where((v) => v.locale.startsWith('es-')).toList();
    if (lang == 'FR') return _voices.where((v) => v.locale.startsWith('fr-')).toList();
    return _voices;
  }

  VoiceModel? _currentVoice(CharacterModel char) {
    if (_pendingChanges.containsKey(char.id)) return _pendingChanges[char.id];
    if (char.voiceId == null) return null;
    try { return _voices.firstWhere((v) => v.id == char.voiceId); } catch (_) { return null; }
  }

  Future<void> _save() async {
    if (_pendingChanges.isEmpty) { context.pop(); return; }
    setState(() => _isSaving = true);
    try {
      await Future.wait(_pendingChanges.entries.map((e) =>
          ApiService.instance.updateCharacterVoice(widget.bookId, e.key, e.value.id, e.value.name)));
      if (!mounted) return;
      // Pergunta se quer regenerar o áudio
      final regen = await showDialog<bool>(
        context: context,
        builder: (_) => AlertDialog(
          backgroundColor: AppColors.surfaceCard,
          title: const Text('Vozes salvas!', style: TextStyle(color: AppColors.textPrimary)),
          content: const Text(
            'Deseja regenerar o áudio do livro com as novas vozes?\nIsso pode levar alguns minutos.',
            style: TextStyle(color: AppColors.textSecondary),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(_, false),
              child: const Text('Agora não'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary),
              onPressed: () => Navigator.pop(_, true),
              child: const Text('Regenerar', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      );
      if (regen == true && mounted) {
        setState(() => _isRegenerating = true);
        await ApiService.instance.regenerateAudio(widget.bookId);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Regeneração iniciada! Acompanhe na tela do livro.'),
            backgroundColor: AppColors.success,
            duration: Duration(seconds: 3),
          ));
        }
      }
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) {
        setState(() { _isSaving = false; _isRegenerating = false; });
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Erro: $e'), backgroundColor: AppColors.error,
        ));
      }
    }
  }

  void _openVoicePicker(CharacterModel char) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surfaceCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => _VoicePickerSheet(
        character: char,
        voices: _voices,
        selectedVoiceId: _currentVoice(char)?.id,
        onSelect: (voice) {
          setState(() => _pendingChanges[char.id] = voice);
          Navigator.pop(context);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        title: const Text('Configurar Vozes',
            style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600)),
        leading: IconButton(
          icon: const Icon(Icons.close, color: AppColors.textSecondary),
          onPressed: () => context.pop(),
        ),
        actions: [
          if (_pendingChanges.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppColors.warning.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${_pendingChanges.length} alterado${_pendingChanges.length > 1 ? 's' : ''}',
                    style: const TextStyle(color: AppColors.warning, fontSize: 11, fontWeight: FontWeight.w600),
                  ),
                ),
              ),
            ),
        ],
        bottom: _isLoading ? null : TabBar(
          controller: _tabController,
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          labelColor: AppColors.primary,
          unselectedLabelColor: AppColors.textHint,
          indicatorColor: AppColors.primary,
          tabs: _langs.map((l) {
            final count = _filteredVoices(l).length;
            return Tab(text: '$l ($count)');
          }).toList(),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : _error != null
              ? _ErrorView(error: _error!, onRetry: _load)
              : Column(
                  children: [
                    // Info banner
                    Container(
                      margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: AppColors.primary.withOpacity(0.2)),
                      ),
                      child: Row(
                        children: const [
                          Icon(Icons.info_outline, color: AppColors.primary, size: 16),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Toque em um personagem para escolher sua voz. Use as abas para filtrar por idioma.',
                              style: TextStyle(color: AppColors.textSecondary, fontSize: 12, height: 1.4),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),
                    // Lista de personagens
                    Expanded(
                      child: ListView.separated(
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
                        itemCount: _characters.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, i) {
                          final char = _characters[i];
                          return _CharacterVoiceCard(
                            character: char,
                            currentVoice: _currentVoice(char),
                            hasChange: _pendingChanges.containsKey(char.id),
                            availableCount: _filteredVoices(_langs[_tabController.index]).length,
                            onTap: () => _openVoicePickerFiltered(char),
                          );
                        },
                      ),
                    ),
                  ],
                ),
      bottomNavigationBar: _isLoading
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: ElevatedButton(
                  onPressed: (_isSaving || _isRegenerating) ? null : _save,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _pendingChanges.isEmpty ? AppColors.surfaceVariant : AppColors.primary,
                    foregroundColor: Colors.white,
                    minimumSize: const Size(double.infinity, 52),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  child: (_isSaving || _isRegenerating)
                      ? Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const SizedBox(width: 20, height: 20,
                                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)),
                            const SizedBox(width: 10),
                            Text(_isRegenerating ? 'Iniciando regeneração...' : 'Salvando...'),
                          ],
                        )
                      : Text(
                          _pendingChanges.isEmpty
                              ? 'Fechar'
                              : 'Salvar ${_pendingChanges.length} alteração${_pendingChanges.length > 1 ? 'ões' : ''}',
                          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
                        ),
                ),
              ),
            ),
    );
  }

  void _openVoicePickerFiltered(CharacterModel char) {
    final currentLang = _langs[_tabController.index];
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surfaceCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => _VoicePickerSheet(
        character: char,
        voices: _voices,
        selectedVoiceId: _currentVoice(char)?.id,
        initialLang: currentLang == 'Todos' ? null : currentLang,
        onSelect: (voice) {
          setState(() => _pendingChanges[char.id] = voice);
          Navigator.pop(context);
        },
      ),
    );
  }
}

// ── Card de personagem ────────────────────────────────────────────────────────

class _CharacterVoiceCard extends StatelessWidget {
  final CharacterModel character;
  final VoiceModel? currentVoice;
  final bool hasChange;
  final int availableCount;
  final VoidCallback onTap;

  const _CharacterVoiceCard({
    required this.character, required this.currentVoice,
    required this.hasChange, required this.availableCount, required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.surfaceCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: hasChange ? AppColors.primary.withOpacity(0.6) : AppColors.border,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 46, height: 46,
              decoration: BoxDecoration(
                color: character.colorValue.withOpacity(0.2),
                shape: BoxShape.circle,
                border: Border.all(color: character.colorValue, width: 2),
              ),
              child: Center(
                child: Text(
                  character.name.isNotEmpty ? character.name[0].toUpperCase() : '?',
                  style: TextStyle(color: character.colorValue, fontWeight: FontWeight.w700, fontSize: 18),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(character.name,
                          style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600, fontSize: 15),
                          overflow: TextOverflow.ellipsis),
                      ),
                      if (character.isNarrator) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text('Narrador',
                            style: TextStyle(color: AppColors.primary, fontSize: 10, fontWeight: FontWeight.w600)),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.mic, size: 13, color: AppColors.textSecondary),
                      const SizedBox(width: 4),
                      Flexible(
                        child: Text(
                          currentVoice != null
                              ? '${currentVoice!.name} · ${currentVoice!.localeName}'
                              : 'Nenhuma voz',
                          style: TextStyle(
                            color: currentVoice != null ? AppColors.textSecondary : AppColors.textHint,
                            fontSize: 12,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (hasChange) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                          decoration: BoxDecoration(
                            color: AppColors.warning.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Text('alterado',
                            style: TextStyle(color: AppColors.warning, fontSize: 10)),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const Icon(Icons.chevron_right, color: AppColors.textHint),
          ],
        ),
      ),
    );
  }
}

// ── Bottom Sheet com abas de idioma ───────────────────────────────────────────

class _VoicePickerSheet extends StatefulWidget {
  final CharacterModel character;
  final List<VoiceModel> voices;
  final String? selectedVoiceId;
  final String? initialLang;
  final void Function(VoiceModel) onSelect;

  const _VoicePickerSheet({
    required this.character, required this.voices,
    required this.selectedVoiceId, this.initialLang, required this.onSelect,
  });

  @override
  State<_VoicePickerSheet> createState() => _VoicePickerSheetState();
}

class _VoicePickerSheetState extends State<_VoicePickerSheet> with SingleTickerProviderStateMixin {
  late TabController _tabCtrl;
  static const _tabs = ['Todos', 'PT-BR', 'EN', 'ES', 'FR'];

  @override
  void initState() {
    super.initState();
    final initialIndex = widget.initialLang != null
        ? _tabs.indexOf(widget.initialLang!).clamp(0, _tabs.length - 1)
        : 0;
    _tabCtrl = TabController(length: _tabs.length, vsync: this, initialIndex: initialIndex);
  }

  @override
  void dispose() { _tabCtrl.dispose(); super.dispose(); }

  List<VoiceModel> _forTab(String tab) {
    if (tab == 'Todos') return widget.voices;
    if (tab == 'PT-BR') return widget.voices.where((v) => v.locale.startsWith('pt-BR')).toList();
    if (tab == 'EN') return widget.voices.where((v) => v.locale.startsWith('en-')).toList();
    if (tab == 'ES') return widget.voices.where((v) => v.locale.startsWith('es-')).toList();
    if (tab == 'FR') return widget.voices.where((v) => v.locale.startsWith('fr-')).toList();
    return widget.voices;
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.85,
      maxChildSize: 0.95,
      minChildSize: 0.5,
      builder: (_, scrollCtrl) => Column(
        children: [
          // Handle
          Center(
            child: Container(
              margin: const EdgeInsets.only(top: 12, bottom: 8),
              width: 40, height: 4,
              decoration: BoxDecoration(color: AppColors.border, borderRadius: BorderRadius.circular(2)),
            ),
          ),
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 8),
            child: Row(
              children: [
                Container(
                  width: 36, height: 36,
                  decoration: BoxDecoration(
                    color: widget.character.colorValue.withOpacity(0.2), shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(widget.character.name[0].toUpperCase(),
                      style: TextStyle(color: widget.character.colorValue, fontWeight: FontWeight.w700, fontSize: 16)),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(widget.character.name,
                        style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 16)),
                      const Text('Escolha uma voz',
                        style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          // Abas de idioma
          TabBar(
            controller: _tabCtrl,
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            labelColor: AppColors.primary,
            unselectedLabelColor: AppColors.textHint,
            indicatorColor: AppColors.primary,
            dividerColor: AppColors.border,
            tabs: _tabs.map((t) => Tab(text: t)).toList(),
          ),
          // Lista de vozes
          Expanded(
            child: TabBarView(
              controller: _tabCtrl,
              children: _tabs.map((tab) {
                final voices = _forTab(tab);
                if (voices.isEmpty) {
                  return const Center(
                    child: Text('Nenhuma voz neste idioma',
                      style: TextStyle(color: AppColors.textHint)),
                  );
                }
                // Agrupar por localidade dentro do tab "Todos"
                final grouped = <String, List<VoiceModel>>{};
                for (final v in voices) {
                  grouped.putIfAbsent(v.localeName, () => []).add(v);
                }
                return ListView(
                  padding: const EdgeInsets.only(bottom: 24),
                  children: grouped.entries.expand((entry) => [
                    _SectionHeader(label: _langLabel(entry.key)),
                    ...entry.value.map((v) => _VoiceTile(
                      voice: v,
                      isSelected: v.id == widget.selectedVoiceId,
                      onTap: () => widget.onSelect(v),
                    )),
                  ]).toList(),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }

  String _langLabel(String code) {
    return switch (code) {
      'PT-BR' => '🇧🇷  Português (Brasil)',
      'EN' => '🇺🇸  Inglês (EUA)',
      'ES' => '🇪🇸  Espanhol',
      'FR' => '🇫🇷  Francês',
      _ => code,
    };
  }
}

class _SectionHeader extends StatelessWidget {
  final String label;
  const _SectionHeader({required this.label});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(16, 14, 16, 6),
    child: Text(label,
      style: const TextStyle(color: AppColors.textHint, fontSize: 12,
          fontWeight: FontWeight.w600, letterSpacing: 0.5)),
  );
}

class _VoiceTile extends StatelessWidget {
  final VoiceModel voice;
  final bool isSelected;
  final VoidCallback onTap;
  const _VoiceTile({required this.voice, required this.isSelected, required this.onTap});

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: isSelected ? AppColors.primary.withOpacity(0.08) : Colors.transparent,
      child: Row(
        children: [
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: voice.gender == 'male'
                  ? AppColors.info.withOpacity(0.12)
                  : AppColors.primary.withOpacity(0.12),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(voice.genderIcon,
                style: TextStyle(fontSize: 16,
                    color: voice.gender == 'male' ? AppColors.info : AppColors.primary)),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(voice.name,
                  style: TextStyle(
                    color: isSelected ? AppColors.primary : AppColors.textPrimary,
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                    fontSize: 15,
                  )),
                Text(voice.gender == 'male' ? 'Masculino' : 'Feminino',
                  style: const TextStyle(color: AppColors.textHint, fontSize: 12)),
              ],
            ),
          ),
          if (isSelected)
            const Icon(Icons.check_circle, color: AppColors.primary, size: 22)
          else
            const Icon(Icons.radio_button_unchecked, color: AppColors.border, size: 22),
        ],
      ),
    ),
  );
}

class _ErrorView extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;
  const _ErrorView({required this.error, required this.onRetry});
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline, color: AppColors.error, size: 48),
          const SizedBox(height: 16),
          Text(error, style: const TextStyle(color: AppColors.textSecondary)),
          const SizedBox(height: 16),
          ElevatedButton(onPressed: onRetry, child: const Text('Tentar novamente')),
        ],
      ),
    ),
  );
}
