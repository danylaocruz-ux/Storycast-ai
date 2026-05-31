import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../core/constants/app_constants.dart';

class ApiService {
  static ApiService? _instance;
  late final Dio _dio;
  final _storage = const FlutterSecureStorage();

  ApiService._() {
    _dio = Dio(BaseOptions(
      baseUrl: AppConstants.baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 60),
      sendTimeout: const Duration(seconds: 60),
      headers: {'Content-Type': 'application/json'},
    ));

    // Interceptor para injetar token automaticamente
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: AppConstants.tokenKey);
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) {
        // Token expirado → limpa sessão
        if (error.response?.statusCode == 401) {
          _storage.delete(key: AppConstants.tokenKey);
        }
        return handler.next(error);
      },
    ));
  }

  static ApiService get instance {
    _instance ??= ApiService._();
    return _instance!;
  }

  Dio get dio => _dio;

  Future<void> setToken(String token) =>
      _storage.write(key: AppConstants.tokenKey, value: token);

  Future<void> clearToken() =>
      _storage.delete(key: AppConstants.tokenKey);

  Future<bool> hasToken() async {
    final token = await _storage.read(key: AppConstants.tokenKey);
    return token != null && token.isNotEmpty;
  }

  // ── Auth ──────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> login(String email, String password) async {
    final resp = await _dio.post('/auth/login', data: {
      'email': email,
      'password': password,
    });
    return resp.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> register(String name, String email, String password) async {
    final resp = await _dio.post('/auth/register', data: {
      'name': name,
      'email': email,
      'password': password,
    });
    return resp.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getMe() async {
    final resp = await _dio.get('/auth/me');
    return resp.data as Map<String, dynamic>;
  }

  // ── Livros ────────────────────────────────────────────────────────────────

  Future<List<dynamic>> getBooks() async {
    final resp = await _dio.get('/books');
    return resp.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> uploadBook(String filePath, String filename) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath, filename: filename),
    });
    final resp = await _dio.post(
      '/books',
      data: formData,
      options: Options(contentType: 'multipart/form-data'),
    );
    return resp.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getBook(int id) async {
    final resp = await _dio.get('/books/$id');
    return resp.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getBookStatus(int id) async {
    final resp = await _dio.get('/books/$id/status');
    return resp.data as Map<String, dynamic>;
  }

  Future<void> deleteBook(int id) => _dio.delete('/books/$id');

  Future<Map<String, dynamic>> toggleFavorite(int id, bool isFavorite) async {
    final resp = await _dio.put('/books/$id', data: {'is_favorite': isFavorite});
    return resp.data as Map<String, dynamic>;
  }

  // ── Personagens ───────────────────────────────────────────────────────────

  Future<List<dynamic>> getCharacters(int bookId) async {
    final resp = await _dio.get('/books/$bookId/characters');
    return resp.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> updateCharacter(
      int bookId, int charId, Map<String, dynamic> data) async {
    final resp = await _dio.put('/books/$bookId/characters/$charId', data: data);
    return resp.data as Map<String, dynamic>;
  }

  Future<List<dynamic>> getAvailableVoices() async {
    final resp = await _dio.get('/voices/available');
    return resp.data as List<dynamic>;
  }

  // ── Segmentos ─────────────────────────────────────────────────────────────

  Future<List<dynamic>> getSegments(int bookId) async {
    final resp = await _dio.get('/books/$bookId/segments');
    return resp.data as List<dynamic>;
  }

  String audioUrl(int bookId, int segmentIndex) =>
      '${AppConstants.baseUrl}/books/$bookId/segments/$segmentIndex/audio';

  // ── Player state ──────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> getPlayerState(int bookId) async {
    final resp = await _dio.get('/books/$bookId/player-state');
    return resp.data as Map<String, dynamic>;
  }

  Future<void> savePlayerState(int bookId, int segment, double position, double speed) async {
    await _dio.put('/books/$bookId/player-state', data: {
      'current_segment': segment,
      'current_position': position,
      'playback_speed': speed,
    });
  }

  // ── Marcadores ────────────────────────────────────────────────────────────

  Future<List<dynamic>> getBookmarks(int bookId) async {
    final resp = await _dio.get('/books/$bookId/bookmarks');
    return resp.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> createBookmark(
      int bookId, int segmentIndex, double position, String? label) async {
    final resp = await _dio.post('/bookmarks', data: {
      'book_id': bookId,
      'segment_index': segmentIndex,
      'position': position,
    