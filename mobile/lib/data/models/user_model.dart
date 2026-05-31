class UserModel {
  final int id;
  final String email;
  final String name;
  final String plan;

  const UserModel({
    required this.id,
    required this.email,
    required this.name,
    required this.plan,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) => UserModel(
        id: json['id'] as int,
        email: json['email'] as String,
        name: json['name'] as String,
        plan: json['plan'] as String? ?? 'free',
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'email': email,
        'name': name,
        'plan': plan,
      };

  String get initials {
    final parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    return name.isNotEmpty ? name[0].toUpperCase() : 'U';
  }
}
