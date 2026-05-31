import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/character_model.dart';
import '../../../data/services/api_service.dart';

class CharactersScreen extends ConsumerStatefulWidget {
  final int bookId;
  const CharactersScreen({super.key, required this.bookId});

  @override
  ConsumerState<CharactersScreen> createState() => _CharactersScreenState();
}

class _CharactersScreenState extends ConsumerState<CharactersScreen> {
  List<CharacterModel> _characters = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await ApiService.instance.getCharacters(widget.bookId);
      setState(() {
        _characters = data.map((e) => CharacterModel.fromJson(e as Map<String, dynamic>)).toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Elenco de personagens'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.go('/home'),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : _error != null
              ? _ErrorView(error: _error!, onRetry: _load)
              : Column(
                  children: [
                    // Header
                    Container(
                      margin: const EdgeInsets.all(16),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        gradient: AppColors.gradientPrimary,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.group, color: Colors.white, size: 32),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${_characters.length} personagens identificados',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w700,
                                    fontSize: 16,
                                  ),
                                ),
                                const Text(
                                  'Cada um com sua própria voz',
                                  style: TextStyle(color: Colors.white70, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),

                    // Lista
                    Expanded(
                      child: ListView.separated(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                        itemCount: _characters.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, idx) => _CharacterTile(
                          character: _characters[idx],
                          onEdit: () => _showEditDialog(_characters[idx]),
                        ),
                      ),
                    ),

                    // Botão escutar
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: () => context.go('/player/${widget.bookId}'),
                          icon: const Icon(Icons.play_arrow),
                          label: const Text('Começar a ouvir'),
                        ),
                      ),
                    ),
                  ],
                ),
    );
  }

  Future<void> _showEditDialog(CharacterModel char) async {
    String? selectedVoiceId = char.voiceId;
    await showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surfaceCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Editar ${char.name}',
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Voz atual: ${char.voiceName ?? "Não atribuída"}',
              style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 24),
            const Text(
              'Para alterar vozes, acesse as configurações do personagem.',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

class _CharacterTile extends StatelessWidget {
  final CharacterModel character;
  final VoidCallback onEdit;

  const _CharacterTile({required this.character, required this.onEdit});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          // Avatar colorido
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: character.colorValue.withOpacity(0.2),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: character.colorValue, width: 2),
            ),
            child: Center(
              child: Text(
                character.name[0].toUpperCase(),
                style: TextStyle(
                  color: character.colorValue,
                  fontWeight: FontWeight.w700,
                  fontSize: 18,
                ),
              ),
            ),
          ),
          const SizedBox(width: 14),
          // Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      character.name,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 15,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    if (character.isNarrator) ...[
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          'NARRADOR',
                          style: TextStyle(
                            fontSize: 9,
                            color: AppColors.primary,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Text(
                      '${character.genderIcon} ${character.ageLabel}',
                      style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                    ),
                    if (character.voiceName != null) ...[
                      const Text(' · ', style: TextStyle(color: AppColors.textHint)),
                      const Icon(Icons.mic, size: 12, color: AppColors.textSecondary),
                      const SizedBox(width: 2),
                      Text(
                        character.voiceName!,
                        style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                      ),
                    ],
                  ],
                ),
                if (character.description != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    character.description!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11, color: AppColors.textHint),
                  ),
                ],
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.edit_outlined, color: AppColors.textSecondary, size: 18),
            onPressed: onEdit,
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;
  const _ErrorView({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, color: AppColors.error, size: 56),
            const SizedBox(height: 16),
            const Text(
              'Erro ao carregar personagens',
              style: TextStyle(color: AppColors.textPrimary, fontSize: 16, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text(error, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
            const SizedBox(height: 24),
            ElevatedButton(onPressed: onRetry, child: const Text('Tentar novamente')),
          ],
        ),
      ),
    );
  }
}
