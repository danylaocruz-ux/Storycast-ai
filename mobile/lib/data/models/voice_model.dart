class VoiceModel {
  final String id;
  final String name;
  final String locale;
  final String gender;

  const VoiceModel({
    required this.id,
    required this.name,
    required this.locale,
    required this.gender,
  });

  factory VoiceModel.fromJson(Map<String, dynamic> json) => VoiceModel(
        id: json['id'] as String,
        name: json['name'] as String,
        locale: json['locale'] as String? ?? 'pt-BR',
        gender: json['gender'] as String? ?? 'neutral',
      );

  String get genderIcon => gender == 'male' ? '♂' : gender == 'female' ? '♀' : '⚬';

  String get localeName {
    if (locale.startsWith('pt-BR')) return 'PT-BR';
    if (locale.startsWith('en-US')) return 'EN';
    return locale;
  }

  bool get isPtBr => locale.startsWith('pt-BR');
}
