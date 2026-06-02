import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../auth/providers/auth_provider.dart';
import '../../library/providers/library_provider.dart';
import '../../../shared/widgets/book_card.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(libraryProvider.notifier).load());
  }

  Future<void> _confirmDelete(BuildContext context, int bookId, String title) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surfaceCard,
        title: const Text('Cancelar processamento?',
            style: TextStyle(color: AppColors.textPrimary)),
        content: Text(
          'Deseja excluir "$title"?\nO processamento será interrompido e o arquivo removido.',
          style: const TextStyle(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(_, false),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(_, true),
            child: const Text('Excluir', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
    if (confirm == true && context.mounted) {
      ref.read(libraryProvider.notifier).deleteBook(bookId);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final library = ref.watch(libraryProvider);
    final user = auth.user;

    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            // ── Header ────────────────────────────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Olá, ${user?.name.split(' ').first ?? 'Leitor'} 👋',
                            style: const TextStyle(
                              fontSize: 22, fontWeight: FontWeight.w700, color: AppColors.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 4),
                          const Text(
                            'O que vamos ouvir hoje?',
                            style: TextStyle(fontSize: 14, color: AppColors.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    GestureDetector(
                      onTap: () => context.go('/settings'),
                      child: Container(
                        width: 44, height: 44,
                        decoration: BoxDecoration(
                          gradient: AppColors.gradientPrimary,
                          borderRadius: BorderRadius.circular(22),
                        ),
                        child: Center(
                          child: Text(
                            user?.initials ?? 'U',
                            style: const TextStyle(
                              color: Colors.white, fontWeight: FontWeight.w700, fontSize: 16,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SliverToBoxAdapter(child: SizedBox(height: 32)),

            // ── Banner upload ─────────────────────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: _UploadBanner(onTap: () => context.go('/upload')),
              ),
            ),

            const SliverToBoxAdapter(child: SizedBox(height: 32)),

            // ── Continuar ouvindo ─────────────────────────────────────────
            if (library.books.any((b) => b.isReady)) ...[
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(24, 0, 24, 16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Continuar ouvindo',
                        style: TextStyle(
                          fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.textPrimary,
                        ),
                      ),
                      TextButton(
                        onPressed: () => context.go('/library'),
                        child: const Text('Ver todos'),
                      ),
                    ],
                  ),
                ),
              ),
              SliverToBoxAdapter(
                child: SizedBox(
                  height: 220,
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    scrollDirection: Axis.horizontal,
                    itemCount: library.books.where((b) => b.isReady).take(5).length,
                    separatorBuilder: (_, __) => const SizedBox(width: 12),
                    itemBuilder: (_, idx) {
                      final readyBooks = library.books.where((b) => b.isReady).take(5).toList();
                      return BookCardHorizontal(
                        book: readyBooks[idx],
                        onTap: () => context.go('/player/${readyBooks[idx].id}'),
                      );
                    },
                  ),
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: 32)),
            ],

            // ── Processando (com botão excluir) ───────────────────────────
            if (library.books.any((b) => b.isProcessing)) ...[
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(24, 0, 24, 16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: const [
                      Text(
                        'Processando',
                        style: TextStyle(
                          fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.textPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (ctx, idx) {
                    final processing = library.books.where((b) => b.isProcessing).toList();
                    final book = processing[idx];
                    return Padding(
                      padding: const EdgeInsets.fromLTRB(24, 0, 24, 12),
                      child: BookCardProcessing(
                        book: book,
                        onTap: () => context.go('/processing/${book.id}'),
                        onDelete: () => _confirmDelete(context, book.id, book.title),
                      ),
                    );
                  },
                  childCount: library.books.where((b) => b.isProcessing).length,
                ),
              ),
            ],

            const SliverToBoxAdapter(child: SizedBox(height: 100)),
          ],
        ),
      ),
    );
  }
}

class _UploadBanner extends StatelessWidget {
  final VoidCallback onTap;
  const _UploadBanner({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: AppColors.gradientPrimary,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text(
                    'Adicionar livro',
                    style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w700),
                  ),
                  SizedBox(height: 4),
                  Text('PDF, EPUB, DOCX ou TXT',
                    style: TextStyle(color: Colors.white70, fontSize: 13)),
                ],
              ),
            ),
            Container(
              width: 56, height: 56,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Icon(Icons.add, color: Colors.white, size: 32),
            ),
          ],
        ),
      ),
    );
  }
}
