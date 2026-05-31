import 'package:flutter/material.dart';
import 'package:percent_indicator/linear_percent_indicator.dart';
import '../../core/constants/app_colors.dart';
import '../../data/models/book_model.dart';

// ── Card horizontal (lista principal) ─────────────────────────────────────────

class BookCardHorizontal extends StatelessWidget {
  final BookModel book;
  final VoidCallback onTap;

  const BookCardHorizontal({super.key, required this.book, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 140,
        decoration: BoxDecoration(
          color: AppColors.surfaceCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Capa
            Container(
              height: 130,
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
              ),
              child: Center(
                child: Icon(
                  _formatIcon(book.format),
                  color: AppColors.primary,
                  size: 48,
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    book.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    book.durationFormatted,
                    style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _formatIcon(String fmt) {
    const map = {'pdf': Icons.picture_as_pdf, 'epub': Icons.menu_book, 'docx': Icons.article, 'txt': Icons.text_snippet};
    return map[fmt] ?? Icons.book;
  }
}

// ── Card processando ───────────────────────────────────────────────────────────

class BookCardProcessing extends StatelessWidget {
  final BookModel book;
  final VoidCallback onTap;

  const BookCardProcessing({super.key, required this.book, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surfaceCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.auto_stories, color: AppColors.primary),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    book.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 6),
                  LinearPercentIndicator(
                    padding: EdgeInsets.zero,
                    lineHeight: 4,
                    percent: book.progress / 100,
                    backgroundColor: AppColors.surfaceVariant,
                    progressColor: AppColors.primary,
                    barRadius: const Radius.circular(4),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    book.statusMessage ?? 'Processando...',
                    style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Card da biblioteca (lista vertical) ───────────────────────────────────────

class BookCardList extends StatelessWidget {
  final BookModel book;
  final VoidCallback onTap;
  final VoidCallback? onFavorite;
  final VoidCallback? onDelete;

  const BookCardList({
    super.key,
    required this.book,
    required this.onTap,
    this.onFavorite,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surfaceCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            // Ícone
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(_formatIcon(book.format), color: AppColors.primary, size: 28),
            ),
            const SizedBox(width: 14),
            // Info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    book.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  if (book.author != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      book.author!,
                      style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                    ),
                  ],
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      _StatusChip(status: book.status),
                      const SizedBox(width: 8),
                      if (book.isReady)
                        Text(
                          book.durationFormatted,
                          style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            // Ações
            Column(
              children: [
                if (onFavorite != null)
                  IconButton(
                    icon: Icon(
                      book.isFavorite ? Icons.favorite : Icons.favorite_border,
                      color: book.isFavorite ? AppColors.error : AppColors.textSecondary,
                      size: 20,
                    ),
                    onPressed: onFavorite,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                  ),
                if (onDelete != null)
                  IconButton(
                    icon: const Icon(Icons.delete_outline, color: AppColors.textHint, size: 20),
                    onPressed: onDelete,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  IconData _formatIcon(String fmt) {
    const map = {'pdf': Icons.picture_as_pdf, 'epub': Icons.menu_book, 'docx': Icons.article, 'txt': Icons.text_snippet};
    return map[fmt] ?? Icons.book;
  }
}

class _StatusChip extends StatelessWidget {
  final String status;
  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    final (color, label) = switch (status) {
      'ready' => (AppColors.success, 'Pronto'),
      'error' => (AppColors.error, 'Erro'),
      _ => (AppColors.warning, 'Processando'),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}
