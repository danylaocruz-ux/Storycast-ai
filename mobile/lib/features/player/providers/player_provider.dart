import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:just_audio/just_audio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../core/constants/app_constants.dart';
import '../../../data/models/audio_segment_model.dart';
import '../../../data/models/character_model.dart';
import '../../../data/models/book_model.dart';
import '../../../data/services/api_service.dart';

enum PlayerStatus { idle, loading, playing, paused, error }

class PlayerState {
  final BookModel? book;
  final List<AudioSegmentModel> segments;
  final List<CharacterModel> characters;
  final int currentIndex;
  final PlayerStatus status;
  final double speed;
  final Duration position;
  final Duration duration;
  final String? error;

  const PlayerState({
    this.book,
    this.segments = const [],
    this.characters = const [],
    this.currentIndex = 0,
    this.status = PlayerStatus.idle,
    this.speed = 1.0,
    this.position = Duration.zero,
    this.duration = Duration.zero,
    this.error,
  });

  AudioSegmentModel? get currentSegment =>
      segments.isNotEmpty && currentIndex < segments.length
          ? segments[currentIndex]
          : null;

  CharacterModel? characterFor(int? charId) =>
      charId == null ? null : characters.where((c) => c.id == charId).firstOrNull;

  bool get isPlaying => status == PlayerStatus.playing;
  bool get isLoading => status == PlayerStatus.loading;

  PlayerState copyWith({
    BookModel? book,
    List<AudioSegmentModel>? segments,
    List<CharacterModel>? characters,
    int? currentIndex,
    PlayerStatus? status,
    double? speed,
    Duration? position,
    Duration? duration,
    String? error,
  }) =>
      PlayerState(
        book: book ?? this.book,
        segments: segments ?? this.segments,
        characters: characters ?? this.characters,
        currentIndex: currentIndex ?? this.currentIndex,
        status: status ?? this.status,
        speed: speed ?? this.speed,
        position: position ?? this.position,
        duration: duration ?? this.duration,
        error: error,
      );
}

class PlayerNotifier extends StateNotifier<PlayerState> {
  final ApiService _api = ApiService.instance;
  final AudioPlayer _player = AudioPlayer();
  final _storage = const FlutterSecureStorage();
  Timer? _saveTimer;
  StreamSubscription? _positionSub;
  StreamSubscription? _statusSub;
  StreamSubscription? _durationSub;

  PlayerNotifier() : super(const PlayerState()) {
    _setupListeners();
  }

  void _setupListeners() {
    _positionSub = _player.positionStream.listen((pos) {
      state = state.copyWith(position: pos);
    });

    _durationSub = _player.durationStream.listen((dur) {
      if (dur != null) state = state.copyWith(duration: dur);
    });

    _statusSub = _player.playerStateStream.listen((ps) {
      if (ps.processingState == ProcessingState.completed) {
        _onSegmentCompleted();
      } else if (ps.playing) {
        state = state.copyWith(status: PlayerStatus.playing);
      } else if (ps.processingState == ProcessingState.loading ||
          ps.processingState == ProcessingState.buffering) {
        state = state.copyWith(status: PlayerStatus.loading);
      } else if (!ps.playing && state.status != PlayerStatus.idle) {
        state = state.copyWith(status: PlayerStatus.paused);
      }
    });
  }

  Future<void> loadBook(BookModel book) async {
    state = state.copyWith(
      book: book,
      status: PlayerStatus.loading,
      currentIndex: 0,
      error: null,
    );

    try {
      final segData = await _api.getSegments(book.id);
      final charData = await _api.getCharacters(book.id);
      final savedState = await _api.getPlayerState(book.id);

      final segments = segData.map((e) => AudioSegmentModel.fromJson(e as Map<String, dynamic>)).toList();
      final characters = charData.map((e) => CharacterModel.fromJson(e as Map<String, dynamic>)).toList();
      final ps = PlayerStateModel.fromJson(savedState);

      state = state.copyWith(
        segments: segments,
        characters: characters,
        currentIndex: ps.currentSegment.clamp(0, segments.length - 1),
        speed: ps.playbackSpeed,
        status: PlayerStatus.paused,
      );

      await _loadSegment(state.currentIndex);
    } catch (e) {
      state = state.copyWith(status: PlayerStatus.error, error: e.toString());
    }
  }

  Future<void> _loadSegment(int index) async {
    if (index < 0 || index >= state.segments.length) return;
    final seg = state.segments[index];
    if (!seg.hasAudio) {
      state = state.copyWith(currentIndex: index, status: PlayerStatus.paused);
      return;
    }

    try {
      final url = _api.audioUrl(state.book!.id, seg.segmentIndex);
      // Lê o token do secure storage para autenticar o stream de áudio
      final token = await _storage.read(key: AppConstants.tokenKey);
      await _player.setAudioSource(
        AudioSource.uri(
          Uri.parse(url),
          headers: token != null ? {'Authorization': 'Bearer $token'} : {},
        ),
      );
      await _player.setSpeed(state.speed);
      state = state.copyWith(currentIndex: index);
    } catch (e) {
      state = state.copyWith(error: 'Erro ao carregar áudio: $e');
    }
  }

  Future<void> play() async {
    if (state.currentSegment == null) return;
    await _player.play();
    _scheduleSave();
  }

  Future<void> pause() async {
    await _player.pause();
    _cancelSave();
    await _persistState();
  }

  Future<void> next() async {
    final next = state.currentIndex + 1;
    if (next >= state.segments.length) return;
    await _player.stop();
    await _loadSegment(next);
    await _player.play();
  }

  Future<void> previous() async {
    final prev = state.currentIndex - 1;
    if (prev < 0) {
      await _player.seek(Duration.zero);
      return;
    }
    await _player.stop();
    await _loadSegment(prev);
    await _player.play();
  }

  Future<void> seekTo(Duration position) async {
    await _player.seek(position);
  }

  Future<void> setSpeed(double speed) async {
    await _player.setSpeed(speed);
    state = state.copyWith(speed: speed);
  }

  Future<void> jumpToSegment(int index) async {
    final wasPlaying = state.isPlaying;
    await _player.stop();
    await _loadSegment(index);
    if (wasPlaying) await _player.play();
  }

  void _onSegmentCompleted() {
    final next = state.currentIndex + 1;
    if (next < state.segments.length) {
      _loadSegment(next).then((_) => _player.play());
    } else {
      state = state.copyWith(status: PlayerStatus.paused);
      _persistState();
    }
  }

  void _scheduleSave() {
    _saveTimer?.cancel();
    _saveTimer = Timer.periodic(const Duration(seconds: 10), (_) => _persistState());
  }

  void _cancelSave() {
    _saveTimer?.cancel();
    _saveTimer = null;
  }

  Future<void> _persistState() async {
    if (state.book == null) return;
    try {
      await _api.savePlayerState(
        state.book!.id,
        state.currentIndex,
        state.position.inSeconds.toDouble(),
        state.speed,
      );
    } catch (_) {}
  }

  @override
  void dispose() {
    _cancelSave();
    _positionSub?.cancel();
    _statusSub?.cancel();
    _durationSub?.cancel();
    _player.dispose();
    super.dispose();
  }
}

final playerProvider = StateNotifierProvi