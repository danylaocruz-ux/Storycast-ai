class AppConstants {
  AppConstants._();

  // Troque pelo IP da máquina onde o backend roda (ou use 10.0.2.2 para emulador Android)
  static const baseUrl = 'http://10.0.2.2:8000/api/v1';

  // Tokens
  static const tokenKey = 'auth_token';
  static const userKey = 'user_data';

  // Player
  static const defaultSpeed = 1.0;
  static const speedOptions = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];

  // Formatos
  static const supportedFormats = ['pdf', 'epub', 'docx', 'txt'];

  // Paginação
  static const pageSize = 20;

  // Polling de status (ms)
  static const statusPollInterval = 3000;

  // Animações
  static const animDurationFast = Duration(milliseconds: 200);
  static const animDurationNormal = Duration(milliseconds: 350);
  static const animDurationSlow = Duration(milliseconds: 600);
}
