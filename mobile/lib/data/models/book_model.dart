class BookModel {
  final int id;
  final String title;
  final String? author;
  final String format;
  final String? coverPath;
  final double totalDuration;
  final int totalSegments;
  final String status;
  final String? statusMessage;
  final int progress;
  final bool isFavorite;
  final DateTime createdAt;

  const BookModel({
    required this.id,
    required this.title,
    this.author,
    required this.format,
    this.coverPath,
    required this.totalDuration,
    required this.totalSegments,
    required this.status,
    this.statusMessage,
    required this.progress,
    required this.isFavorite,
    required this.createdAt,
  });

  factory BookModel.fromJson(Map<String, dynamic> json) => BookModel(
        id: json['id'] as int,
        title: json['title'] as String,
        author: json['author'] as String?,
        format: json['format'] as String,
        coverPath: json['cover_path'] as String?,
        totalDuration: (json['total_duration'] as num?)?.toDouble() ?? 0.0,
        totalSegments: (json['total_segments'] as num?)?.toInt() ?? 0,
        status: json['status'] as String? ?? 'pending',
        statusMessage: json['status_message'] as String?,
        progress: (json['progress'] as num?)?.toInt() ?? 0,
        isFavorite: json['is_favorite'] as bool? ?? false,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  bool get isReady => status == 'ready';
  bool get isProcessing => ['pending', 'extracting', 'analyzing', 'generating_audio'].contains(status);
  bool get hasError => status == 'error';

  String get durationFormatted {
    final d = Duration(seconds: totalDuration.toInt());
    final h = d.inHours;
    final m = d.inMinutes.remainder(60);
    if (h > 0) return '${h}h ${m}min';
    return '${m}min';
  }

  BookModel copyWith({bool? isFavorite}) => BookModel(
        id: id,
        title: title,
        author: author,
        format: format,
        coverPath: coverPath,
        totalDuration: totalDuration,
        totalSegments: totalSegments,
        status: status,
        statusMessage: statusMessage,
        progress: progress,
        isFavorite: isFavorite ?? this.isFavorite,
        createdAt: createdAt,
      );
}

class BookStatusModel {
  final int id;
  final String status;
  final int progress;
  final String? statusMessage;
  final int totalSegments;
  final double totalDuration;

  const BookStatusModel({
    required this.id,
    required this.status,
    required this.progress,
    this.statusMessage,
    required this.totalSegments,
    required this.totalDuration,
  });

  factory BookStatusModel.fromJson(Map<String, dynamic> json) => BookStatusModel(
        id: json['id'] as int,
        status: json['status'] as String,
        progress: (json['progress'] as num).toInt(),
        statusMessage: json['status_message'] as String?,
        totalSegments: (json['total_segments'] as num).toInt(),
        totalDuration: (json['total_duration'] as num).toDouble(),
      );
}
