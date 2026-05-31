import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:percent_indicator/circular_percent_indicator.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_constants.dart';
import '../../../data/models/book_model.dart';
import '../../../data/services/api_service.dart';
import '../../library/providers/library_provider.dart';

class ProcessingScreen extends ConsumerStatefulWidget {
  final int bookId;
  const ProcessingScreen({super.key, required this.bookId});

  @override
  ConsumerState<ProcessingScreen> createState() => _ProcessingScreenState();
}

class _ProcessingScreenState extends ConsumerState<ProcessingScreen> {
  Timer? _pollTimer;
  BookStatusModel? _status;
  bool _navigated = false;

  @override
  void initState() {
    super.initState();
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  void _startPolling() {
    _poll();
    _pollTimer = Timer.periodic(
      const Duration(milliseconds: AppConstants.statusPollInterval),
      (_) => _poll(),
    );
  }

  Future<void> _poll() async {
    try {
      final data = await ApiService.instance.getBookStatus(widget.bookId);
      final status = BookStatusModel.fromJson(data);
      if (mounted) {
        setState(() => _status = status);
        ref.read(libraryProvider.notifier).updateBookStatus(status);

        if (!_navigated && status.status == 'ready') {
          _navigated = true;
          _pollTimer?.cancel();
          // Pequeno delay para mostrar 100%
          await Future.delayed(const Duration(milliseconds: 800));
          if (mounted) context.go('/characters/${widget.bookId}');
        } else if (status.status == 'error') {
          _pollTimer?.cancel();
        }
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final status = _status;
    final progress = status?.progress ?? 0;
    final isError = status?.status == 'error';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Processando livro'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.go('/home'),
        ),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Progresso circular
              CircularPercentIndicator(
                radius: 90,
                lineWidth: 10,
                percent: progress / 100,
                center: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '$progress%',
                      style: const TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    if (!isError)
                      const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: AppColors.primary,
                        ),
                      ),
                  ],
                ),
                progressColor: isError ? AppColors.error : AppColors.primary,
                backgroundColor: AppColors.surfaceVariant,
                animation: true,
                animateFromLastPercent: true,
                circularStrokeCap: CircularStrokeCap.round,
              ),

              const SizedBox(height: 40),

              Text(
                isError ? 'Erro no processamento' : _phaseTitle(status?.status),
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  color: isError ? AppColors.error : AppColors.textPrimary,
                ),
              ),

              const SizedBox(height: 8),

              Text(
                status?.statusMessage ?? 'Iniciando...',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 14,
                  color: AppColors.textSecondary,
                ),
              ),

              const SizedBox(height: 48),

              // Fases
              _PhaseList(currentStatus: status?.status ?? 'pending'),

              const SizedBox(height: 32),

              if (isError)
                ElevatedButton.icon(
                  onPressed: () => context.go('/library'),
                  icon: const Icon(Icons.arrow_back),
                  label: const Text('Voltar à biblioteca'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.error,
                  ),
                )
              else
                TextButton(
                  onPressed: () => context.go('/home'),
                  child: const Text(
                    'Ir para Home (processará em segundo plano)',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  String _phaseTitle(String? s) => switch (s) {
        'extracting' => 'Extraindo texto',
        'analyzing' => 'Analisando narrativa',
        'generating_audio' => 'Gerando áudio',
        'ready' => 'Concluído!',
        _ => 'Preparando',
      };
}

class _PhaseList extends StatelessWidget {
  final String currentStatus;
  const _PhaseList({required this.currentStatus});

  @override
  Widget build(BuildContext context) {
    const phases = [
      ('extracting', Icons.text_fields, 'Extração de texto'),
      ('analyzing', Icons.psychology, 'Análise de personagens'),
      ('generating_audio', Icons.record_voice_over, 'Geração de áudio'),
      ('ready', Icons.check_circle, 'Concluído'),
    ];

    final order = ['pending', 'extracting', 'analyzing', 'generating_audio', 'ready'];
    final currentIdx = order.indexOf(currentStatus);

    return Column(
      children: phases.map((phase) {
        final (id, icon, label) = phase;
        final phaseIdx = order.indexOf(id);
        final isDone = phaseIdx < currentIdx;
        final isCurrent = id == currentStatus;

        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: isDone
                      ? AppColors.success.withOpacity(0.15)
                      : isCurrent
                          ? AppColors.primary.withOpacity(0.15)
                          : AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Icon(
                  isDone ? Icons.check : icon,
                  color: isDone
                      ? AppColors.success
                      : isCurrent
                          ? AppColors.primary
                          : AppColors.textHint,
                  size: 18,
                ),
              ),
              const SizedBox(width: 12),
              Text(
                label,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: isCurrent ? FontWeight.w600 : FontWeight.normal,
                  color: isDone || isCurrent ? AppColors.textPrimary : AppColors.textHint,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}
