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

class _VoiceConfigScreenState extends ConsumerState<VoiceConfigScreen> {
  List<CharacterModel> _characters = [];
  List<VoiceModel> _voices = [];
  // charId → VoiceModel selecionada (somente mudanças pendentes)
  final Map<int, VoiceModel> _pendingChanges = {};
  bool _isLoading = true;
  bool _isSaving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
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
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  VoiceModel? _currentVoice(CharacterModel char) {
    if (_pendingChanges.containsKey(char.id)) return _pendingChanges[char.id];
    if (char.voiceId == null) return null;
    try {
      return _voices.firstWhere((v) => v.id == char.voiceId);
    } catch (_) {
      return null;
    }
  }

  Future<void> _save() async {
    if (_pendingChanges.isEmpty) {
      context.pop();
      return;
    }
    setState(() => _isSaving = true);
    try {
      await Future.wait(_pendingChanges.entries.map((e) =>
          ApiService.instance.updateCharacterVoice(
            widget.bookId,
            e.key,
            e.value.id,
            e.value.name,
          )));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Vozes salvas com sucesso!'),
            backgroundColor: AppColors.success,
            duration: Duration(seconds: 2),
          ),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSaving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Erro ao salvar: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    }
  }

  void _openVoicePicker(CharacterModel char) {
    final currentVoice = _currentVoice(char);
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
        selectedVoiceId: currentVoice?.id,
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
        title: const Text(
          'Configurar Vozes',
          style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600),
        ),
        leading: IconButton(
          icon: const Icon(Icons.close, color: AppColors.textSecondary),
          onPressed: () => context.pop(),
        ),
        actions: [
          if (_pendingChanges.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: AppColors.warning,
                  shape: BoxShape.circle,
                ),
              ),
            ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : _error != null
              ? _ErrorView(error: _error!, onRetry: _load)
              : Column(
                  children: [
                    // Cabeçalho explicativo
                    Container(
                      margin: const EdgeInsets.all(16),
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppColors.primary.withOpacity(0.3)),
                      ),
                      child: Row(
                        children: const [
                          Icon(Icons.record_voice_over, color: AppColors.primary, size: 20),
                          SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              'Escolha a voz de cada personagem. As mudanças se aplicam apenas a novos livros processados.',
                              style: TextStyle(
                                color: AppColors.textSecondary,
                                fontSize: 12,
                                height: 1.4,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                    // Lista de personagens
                    Expanded(
                      child: ListView.separated(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
                        itemCount: _characters.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, i) => _CharacterVoiceCard(
                          character: _characters[i],
                          currentVoice: _currentVoice(_characters[i]),
                          hasChange: _pendingChanges.containsKey(_characters[i].id),
                          onTap: () => _openVoicePicker(_characters[i]),
                        ),
                      ),
                    ),
                  ],
                ),
      // Botão Salvar flutuante
      bottomNavigationBar: _isLoading
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: ElevatedButton(
                  onPressed: _isSaving ? null : _save,
                  style: ElevatedButton.styleFrom(
                    backgroundColor:
                        _pendingChanges.isEmpty ? AppColors.surfaceVariant : AppColors.primary,
                    foregroundColor: Colors.white,
                    minimumSize: const Size(double.infinity, 52),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  child: _isSaving
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
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
}

// ── Card de personagem ────────────────────────────────────────────────────────

class _CharacterVoiceCard extends StatelessWidget {
  final CharacterModel character;
  final VoiceModel? currentVoice;
  final bool hasChange;
  final VoidCallback onTap;

  const _CharacterVoiceCard({
    required this.character,
    required this.currentVoice,
    required this.hasChange,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final charColor = character.colorValue;

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
            // Avatar colorido
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: charColor.withOpacity(0.2),
                shape: BoxShape.circle,
                border: Border.all(color: charColor, width: 2),
              ),
              child: Center(
                child: Text(
                  character.name.isNotEmpty ? character.name[0].toUpperCase() : '?',
                  style: TextStyle(
                    color: charColor,
                    fontWeight: FontWeight.w700,
                    fontSize: 18,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),

            // Info personagem
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          character.name,
                          style: const TextStyle(
                            color: AppColors.textPrimary,
                            fontWeight: FontWeight.w600,
                            fontSize: 15,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (character.isNarrator) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text(
                            'Narrador',
                            style: TextStyle(
                              color: AppColors.primary,
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.mic, size: 14, color: AppColors.textSecondary),
                      const SizedBox(width: 4),
                      Flexible(
                        child: Text(
                          currentVoice != null
                              ? '${currentVoice!.name} · ${currentVoice!.localeName}'
                              : 'Nenhuma voz atribuída',
                          style: TextStyle(
                            color: currentVoice != null
                                ? AppColors.textSecondary
                                : AppColors.textHint,
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
                          child: const Text(
                            'alterado',
                            style: TextStyle(
                              color: AppColors.warning,
                              fontSize: 10,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
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

// ── Bottom Sheet de seleção de voz ────────────────────────────────────────────

class _VoicePickerSheet extends StatelessWidget {
  final CharacterModel character;
  final List<VoiceModel> voices;
  final String? selectedVoiceId;
  final void Function(VoiceModel) onSelect;

  const _VoicePickerSheet({
    required this.character,
    required this.voices,
    required this.selectedVoiceId,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    final ptVoices = voices.where((v) => v.isPtBr).toList();
    final enVoices = voices.where((v) => !v.isPtBr).toList();

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.7,
      maxChildSize: 0.9,
      minChildSize: 0.4,
      builder: (_, scrollCtrl) => Column(
        children: [
          // Handle
          Center(
            child: Container(
              margin: const EdgeInsets.only(top: 12, bottom: 8),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.border,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),

          // Título
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: character.colorValue.withOpacity(0.2),
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      character.name[0].toUpperCase(),
                      style: TextStyle(
                        color: character.colorValue,
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        character.name,
                        style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                        ),
                      ),
                      const Text(
                        'Escolha uma voz',
                        style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const Divider(color: AppColors.border, height: 1),

          // Lista com seções
          Expanded(
            child: ListView(
              controller: scrollCtrl,
              padding: const EdgeInsets.only(bottom: 24),
              children: [
                _SectionHeader(label: '🇧🇷  Português (Brasil)'),
                ...ptVoices.map((v) => _VoiceTile(
                      voice: v,
                      isSelected: v.id == selectedVoiceId,
                      onTap: () => onSelect(v),
                    )),
                _SectionHeader(label: '🇺🇸  Inglês (EUA)'),
                ...enVoices.map((v) => _VoiceTile(
                      voice: v,
                      isSelected: v.id == selectedVoiceId,
                      onTap: () => onSelect(v),
                    )),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String label;
  const _SectionHeader({required this.label});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 6),
        child: Text(
          label,
          style: const TextStyle(
            color: AppColors.textHint,
            fontSize: 12,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
      );
}

class _VoiceTile extends StatelessWidget {
  final VoiceModel voice;
  final bool isSelected;
  final VoidCallback onTap;

  const _VoiceTile({required this.voice, required this.isSelected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        color: isSelected ? AppColors.primary.withOpacity(0.08) : Colors.transparent,
        child: Row(
          children: [
            // Ícone de gênero
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: voice.gender == 'male'
                    ? AppColors.info.withOpacity(0.12)
                    : AppColors.primary.withOpacity(0.12),
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Text(
                  voice.genderIcon,
                  style: TextStyle(
                    fontSize: 16,
                    color: voice.gender == 'male' ? AppColors.info : AppColors.primary,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),

            // Nome da voz
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    voice.name,
                    style: TextStyle(
                      color: isSelected ? AppColors.primary : AppColors.textPrimary,
                      fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                      fontSize: 15,
                    ),
                  ),
                  Text(
                    voice.gender == 'male' ? 'Masculino' : 'Feminino',
                    style: const TextStyle(color: AppColors.textHint, fontSize: 12),
                  ),
                ],
              ),
            ),

            // Check
            if (isSelected)
              const Icon(Icons.check_circle, color: AppColors.primary, size: 22)
            else
              const Icon(Icons.radio_button_unchecked, color: AppColors.border, size: 22),
          ],
        ),
      ),
    );
  }
}

// ── Error View ────────────────────────────────────────────────────────────────

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
