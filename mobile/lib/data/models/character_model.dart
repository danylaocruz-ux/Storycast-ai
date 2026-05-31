import 'package:flutter/material.dart';

class CharacterModel {
  final int id;
  final String name;
  final String? description;
  final String gender;
  final String ageGroup;
  final String? personality;
  final bool isNarrator;
  final String? voiceId;
  final String? voiceName;
  final String color;
  final int appearanceOrder;

  const CharacterModel({
    required this.id,
    required this.name,
    this.description,
    required this.gender,
    required this.ageGroup,
    this.personality,
    required this.isNarrator,
    this.voiceId,
    this.voiceName,
    required this.color,
    required this.appearanceOrder,
  });

  factory CharacterModel.fromJson(Map<String, dynamic> json) => CharacterModel(
        id: json['id'] as int,
        name: json['name'] as String,
        description: json['description'] as String?,
        gender: json['gender'] as String? ?? 'neutral',
        ageGroup: json['age_group'] as String? ?? 'adult',
        personality: json['personality'] as String?,
        isNarrator: json['is_narrator'] as bool? ?? false,
        voiceId: json['voice_id'] as String?,
        voiceName: json['voice_name'] as String?,
        color: json['color'] as String? ?? '#7C3AED',
        appearanceOrder: (json['appearance_order'] as num?)?.toInt() ?? 0,
      );

  Color get colorValue {
    final hex = color.replaceAll('#', '');
    return Color(int.parse('FF$hex', radix: 16));
  }

  String get genderIcon {
    if (gender == 'male') return '♂';
    if (gender == 'female') return '♀';
    return '⚬';
  }

  String get ageLabel {
    const map = {
      'child': 'Criança',
      'teen': 'Adolescente',
      'adult': 'Adulto',
      'elderly': 'Idoso',
    };
    return map[ageGroup] ?? ageGroup;
  }
}
