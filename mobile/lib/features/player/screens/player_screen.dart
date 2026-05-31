import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_constants.dart';
import '../../../data/models/book_model.dart';
import '../../../data/services/api_service.dart';
import '../../library/providers/library_provider.dart';
import '../providers/player_provider.dart';

class PlayerScreen extends ConsumerStatefulWidget {
  final int bookId;
  const PlayerScreen({super.key, required this.bookId});

  @override
  ConsumerState<PlayerScreen> createState() => _PlayerScreenState();
}

class _PlayerScreenState extends ConsumerState<PlayerScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      final library = ref.read(libraryProvider);
      var book = library.books.where((b) => b.id == widget.bookId).firstOrNull;
      if (book == null) {
        final data = await ApiService.instance.getBook(widget.bookId);
        book = BookModel.fromJson(data);
      }
      ref.read(playerProvider.notifier).loadBook(book!);
    });
  }

  @override
  Widget build(BuildContext context) {
    final player = ref.watch(playerProvider);
    final book = player.book;
    final segment = player.currentSegment;
    final character = segment != null ? player.characterFor(segment.characterId) : null;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFF0A0A0F), Color(0xFF13131A)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // ── Toolbar ───────────────────────────────────────────────
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.keyboard_arrow_down, color: AppColors.textPrimary),
                      onPressed: () => context.pop(),
                    ),
                    Expanded(
                      child: Text(
                        book?.title ?? '',
                        textAlign: TextAlign.center,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.group_outlined, color: AppColors.textSecondary),
                      onPressed: () => context.go('/characters/${widget.bookId}'),
                    ),
                  ],
                ),
              ),

              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // ── Personagem atual ────────────────────────────
                      if (character != null) ...[
                        Container(
                          width: 100,
                          height: 100,
                          decoration: BoxDecoration(
                            color: character.colorValue.withOpacity(0.2),
                            shape: BoxShape.circle,
                            border: Border.all(color: character.colorValue, width: 3),
                          ),
                          child: Center(
                            child: Text(
                              character.name[0].toUpperCase(),
                              style: TextStyle(
                                color: character.colorValue,
                                fontSize: 36,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          character.name,
                          style: const TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 4),
                        if (character.voiceName != null)
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.mic, size: 14, color: AppColors.textSecondary),
                              const SizedBox(width: 4),
                              Text(
                                character.voiceName!,
                                style: const TextStyle(
                                  color: AppColors.textSecondary,
                                  fontSize: 13,
                                ),
                              ),
                            ],
                          ),
                      ] else ...[
                        Container(
                          width: 100,
                          height: 100,
                          decoration: BoxDecoration(
                            color: AppColors.primary.withOpacity(0.2),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.headphones, color: AppColors.primary, size: 48),
                        ),
                      ],

                      const SizedBox(height: 32),

                      // ── Texto do segmento ───────────────────────────
                      if (segment != null)
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppColors.surfaceCard,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: AppColors.border),
                          ),
                          child: Column(
                            children: [
                              // Emoção
                              if (segment.emotion != 'neutral') ...[
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Container(
                                      width: 8,
                                      height: 8,
                                      decoration: BoxDecoration(
                                        color: AppColors.emotion(segment.emotion),
                                        shape: BoxShape.circle,
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    Text(
                                      _emotionLabel(segment.emotion),
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: AppColors.emotion(segment.emotion),
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 10),
                              ],
                              Text(
                                segment.text,
                                maxLines: 5,
                                overflow: TextOverflow.ellipsis,
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  color: AppColors.textSecondary,
                                  fontSize: 13,
                                  height: 1.6,
                                ),
                              ),
                            ],
                          ),
                        ),

                      const SizedBox(height: 32),

                      // ── Barra de progresso ──────────────────────────
                      Column(
                        children: [
                          SliderTheme(
                            data: SliderTheme.of(context).copyWith(
                              trackHeight: 3,
                              thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
                              activeTrackColor: AppColors.primary,
                              inactiveTrackColor: AppColors.surfaceVariant,
                              thumbColor: AppColors.primary,
                            ),
                            child: Slider(
                              value: player.position.inSeconds.toDouble(),
                              max: player.duration.inSeconds.toDouble().clamp(1, double.infinity),
                              onChanged: (v) => ref
                                  .read(playerProvider.notifier)
                                  .seekTo(Duration(seconds: v.toInt())),
                            ),
                          ),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                _formatDur(player.position),
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                              Text(
                                '${player.currentIndex + 1}/${player.segments.length}',
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                              Text(
                                _formatDur(player.duration),
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),

                      const SizedBox(height: 24),

                      // ── Controles ───────────────────────────────────
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          // Velocidade
                          _SpeedButton(
                            speed: player.speed,
                            onChanged: (s) => ref.read(playerProvider.notifier).setSpeed(s),
                          ),
                          // Anterior
                          IconButton(
                            onPressed: () => ref.read(playerProvider.notifier).previous(),
                            icon: const Icon(
                              Icons.skip_previous_rounded,
                              color: AppColors.textPrimary,
                              size: 36,
                            ),
                          ),
                          // Play/Pause
                          _PlayButton(
                            isPlaying: player.isPlaying,
                            isLoading: player.isLoading,
                            onPlay: () => ref.read(playerProvider.notifier).play(),
                            onPause: () => ref.read(playerProvider.notifier).pause(),
                          ),
                          // Próximo
                          IconButton(
                            onPressed: () => ref.read(playerProvider.notifier).next(),
                            icon: const Icon(
                              Icons.skip_next_rounded,
                              color: AppColors.textPrimary,
                              size: 36,
                            ),
                          ),
                          // Marcador
                          IconButton(
                            onPressed: () => _addBookmark(),
                            icon: const Icon(
                              Icons.bookmark_add_outlined,
                              color: AppColors.textSecondary,
                              size: 28,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _addBookmark() async {
    final player = ref.read(playerProvider);
    if (player.book == null || player.currentSegment == null) return;
    final labelCtrl = TextEditingController();

    final label = await showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surfaceCard,
        title: const Text('Adicionar marcador', style: TextStyle(color: AppColors.textPrimary)),
        content: TextField(
          controller: labelCtrl,
          style: const TextStyle(color: AppColors.textPrimary),
          decoration: const InputDecoration(hintText: 'Nome do marcador (opcional)'),
          autofocus: true,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(_, null), child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(_, labelCtrl.text.trim()),
            child: const Text('Salvar'),
          ),
        ],
      ),
    );

    if (label != null) {
      try {
        await ApiService.instance.createBookmark(
          player.book!.id,
          player.currentSegment!.segmentIndex,
          player.position.inSeconds.toDouble(),
          label.isEmpty ? null : label,
        );
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Marcador salvo!')),
          );
        }
      } catch (_) {}
    }
  }

  String _formatDur(Duration d) {
    final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  String _emotionLabel(String e) => switch (e) {
        'happy' => 'Alegria',
        'sad' => 'Tristeza',
        'angry' => 'Raiva',
        'fearful' => 'Medo',
        'surprised' => 'Surpresa',
        'romantic' => 'Romance',
        'suspenseful' => 'Suspense',
        _ => 'Neutro',
      };
}

// ── Widgets de controle ────────────────────────────────────────────────────────

class _PlayButton extends StatelessWidget {
  final bool isPlaying;
  final bool isLoading;
  final VoidCallback onPlay;
  final VoidCallback onPause;

  const _PlayButton({
    required this.isPlaying,
    required this.isLoading,
    required this.onPlay,
    required this.onPause,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: isLoading ? null : (isPlaying ? onPause : onPlay),
      child: Container(
        width: 72,
        height: 72,
        decoration: const BoxDecoration(
          gradient: AppColors.gradientPrimary,
          shape: BoxShape.circle,
        ),
        child: isLoading
            ? const Center(
                child: SizedBox(
                  width: 28,
                  height: 28,
                  child: CircularProgressIndicator(strokeWidth: 3, color: Colors.white),
                ),
              )
            : Icon(
                isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                color: Colors.white,
                size: 40,
              ),
      ),
    );
  }
}

class _SpeedButton extends StatelessWidget {
  final double speed;
  final ValueChanged<double> onChanged;

  const _SpeedButton({required this.speed, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => showModalBottomSheet(
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
              child: Text(
                'Velocidade de reprodução',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w600,
                  fontSize: 16,
                ),
              ),
            ),
            const Divider(height: 1),
            ...AppConstants.speedOptions.map((s) => ListTile(
                  title: Text(
                    '${s}x',
                    style: TextStyle(
                      color: s == speed ? AppColors.primary : AppColors.textPrimary,
                      fontWeight: s == speed ? FontWeight.w700 : FontWeight.normal,
                    ),
                  ),
                  trailing: s == speed
                      ? const Icon(Icons.check, color: AppColors.primary)
                      : null,
                  onTap: () {
                    onChanged(s);
                    Navigator.pop(_);
                  },
                )),
            const SizedBox(height: 16),
          ],
        ),
      ),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.surfaceVariant,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.border),
        ),
        child: Text(
          '${speed}x',
          style: const TextStyle(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w600,
            fontSize: 14,
          ),
        ),
      ),
    );
  }
}
