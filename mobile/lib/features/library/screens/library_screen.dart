import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../providers/library_provider.dart';
import '../../../shared/widgets/book_card.dart';

class LibraryScreen extends ConsumerStatefulWidget {
  const LibraryScreen({super.key});

  @override
  ConsumerState<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends ConsumerState<LibraryScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    Future.microtask(() => ref.read(libraryProvider.notifier).load());
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final library = ref.watch(libraryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Biblioteca'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => context.go('/upload'),
          ),
        ],
        bottom: TabBar(
          controller: _tabs,
          indicatorColor: AppColors.primary,
          labelColor: AppColors.primary,
          unselectedLabelColor: AppColors.textSecondary,
          tabs: const [
            Tab(text: 'Todos'),
            Tab(text: 'Favoritos'),
            Tab(text: 'Prontos'),
          ],
        ),
      ),
      body: library.isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : TabBarView(
              controller: _tabs,
              children: [
                _BookList(
                  books: library.books,
                  onEmpty: 'Nenhum livro ainda\nAdicione um livro para começar!',
                ),
                _BookList(
                  books: library.favorites,
                  onEmpty: 'Nenhum favorito\nMarque livros como favoritos!',
                ),
                _BookList(
                  books: library.books.where((b) => b.isReady).toList(),
                  onEmpty: 'Nenhum livro pronto ainda',
                ),
              ],
            ),
    );
  }
}

class _BookList extends ConsumerWidget {
  final List<dynamic> books;
  final String onEmpty;

  const _BookList({required this.books, required this.onEmpty});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (books.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(
            onEmpty,
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 15),
          ),
        ),
      );
    }

    return RefreshIndicator(
      color: AppColors.primary,
      onRefresh: () => ref.read(libraryProvider.notifier).load(),
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: books.length,
        separatorBuilder: (_, __) => const SizedBox(height: 12),
        itemBuilder: (_, idx) {
          final book = books[idx];
          return BookCardList(
            book: book,
            onTap: () {
              if (book.isReady) {
                context.go('/player/${book.id}');
              } else if (book.isProcessing) {
                context.go('/processing/${book.id}');
              }
            },
            onFavorite: () => ref.read(libraryProvider.notifier).toggleFavorite(book.id),
            onDelete: () => _confirmDelete(context, ref, book.id, book.title),
          );
        },
      ),
    );
  }

  Future<void> _confirmDelete(BuildContext ctx, WidgetRef ref, int id, String title) async {
    final confirm = await showDialog<bool>(
      context: ctx,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surfaceCard,
        title: const Text('Excluir livro', style: TextStyle(color: AppColors.textPrimary)),
        content: Text(
          'Deseja excluir "$title"?\nEsta ação não pode ser desfeita.',
          style: const TextStyle(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(_, false), child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(_, true),
            child: const Text('Excluir', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
    if (confirm == true) {
      ref.read(libraryProvider.notifier).deleteBook(id);
   