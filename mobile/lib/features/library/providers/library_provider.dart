import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/book_model.dart';
import '../../../data/services/api_service.dart';

class LibraryState {
  final List<BookModel> books;
  final bool isLoading;
  final String? error;

  const LibraryState({
    this.books = const [],
    this.isLoading = false,
    this.error,
  });

  List<BookModel> get favorites => books.where((b) => b.isFavorite).toList();
  List<BookModel> get recent => books.take(5).toList();

  LibraryState copyWith({
    List<BookModel>? books,
    bool? isLoading,
    String? error,
  }) =>
      LibraryState(
        books: books ?? this.books,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

class LibraryNotifier extends StateNotifier<LibraryState> {
  final ApiService _api = ApiService.instance;

  LibraryNotifier() : super(const LibraryState());

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final data = await _api.getBooks();
      final books = data.map((e) => BookModel.fromJson(e as Map<String, dynamic>)).toList();
      state = state.copyWith(books: books, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> toggleFavorite(int bookId) async {
    final idx = state.books.indexWhere((b) => b.id == bookId);
    if (idx == -1) return;

    final book = state.books[idx];
    final newFav = !book.isFavorite;

    // Otimista: atualiza localmente
    final updated = List<BookModel>.from(state.books);
    updated[idx] = book.copyWith(isFavorite: newFav);
    state = state.copyWith(books: updated);

    try {
      await _api.toggleFavorite(bookId, newFav);
    } catch (_) {
      // Reverte em caso de erro
      updated[idx] = book;
      state = state.copyWith(books: updated);
    }
  }

  Future<void> deleteBook(int bookId) async {
    try {
      await _api.deleteBook(bookId);
      state = state.copyWith(
        books: state.books.where((b) => b.id != bookId).toList(),
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  void updateBookStatus(BookStatusModel status) {
    final idx = state.books.indexWhere((b) => b.id == status.id);
    if (idx == -1) return;
    final book = state.books[idx];
    final updated = List<BookModel>.from(state.books);
    updated[idx] = BookModel(
      id: book.id,
      title: book.title,
      author: book.author,
      format: book.format,
      coverPath: book.coverPath,
      totalDuration: status.totalDuration,
      totalSegments: status.totalSegments,
      status: status.status,
      statusMessage: status.statusMessage,
      progress: status.progress,
      isFavorite: book.isFavorite,
      createdAt: book.createdAt,
    );
    state = state.copyWith(books: updated);
  }

  void addBook(BookModel book) {
    state = state.copyWith(books: [book, ...state.books]);
  }
}

final libraryProvider = StateNotifierProvider<LibraryNotifier, LibraryState>(
  (ref) => LibraryNotifier(),
);
