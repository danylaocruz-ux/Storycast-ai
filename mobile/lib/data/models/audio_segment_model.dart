class AudioSegmentModel {
  final int id;
  final int segmentIndex;
  final int chapter;
  final String text;
  final String emotion;
  final String? audioPath;
  final double duration;
  final String status;
  final int? characterId;

  const AudioSegmentModel({
    required this.id,
    required this.segmentIndex,
    required this.chapter,
    required this.text,
    required this.emotion,
    this.audioPath,
    required this.duration,
    required this.status,
    this.characterId,
  });

  factory AudioSegmentModel.fromJson(Map<String, dynamic> json) => AudioSegmentModel(
        id: json['id'] as int,
        segmentIndex: (json['segment_index'] as num).toInt(),
        chapter: (json['chapter'] as num?)?.toInt() ?? 1,
        text: json['text'] as String,
        emotion: json['emotion'] as String? ?? 'neutral',
        audioPath: json['audio_path'] as String?,
        duration: (json['duration'] as num?)?.toDouble() ?? 0.0,
        status: json['status'] as String? ?? 'pending',
        characterId: (json['character_id'] as num?)?.toInt(),
      );

  bool get hasAudio => audioPath != null && status == 'ready';
}

class PlayerStateModel {
  final int currentSegment;
  final double currentPosition;
  final double playbackSpeed;
  final double totalListened;

  const PlayerStateModel({
    this.currentSegment = 0,
    this.currentPosition = 0.0,
    this.playbackSpeed = 1.0,
    this.totalListened = 0.0,
  });

  factory PlayerStateModel.fromJson(Map<String, dynamic> json) => PlayerStateModel(
        currentSegment: (json['current_segment'] as num?)?.toInt() ?? 0,
        currentPosition: (json['current_position'] as num?)?.toDouble() ?? 0.0,
        playbackSpeed: (json['playback_speed'] as num?)?.toDouble() ?? 1.0,
        totalListened: (json['total_listened'] as num?)?.toDouble() ?? 0.0,
      );
}
