# StoryCast AI 🎙️

Transform books and documents into cinematic multi-voice audio experiences powered by GPT-4o and ElevenLabs.

---

## Architecture

```
storycast_ai/
├── backend/          # FastAPI + SQLite + OpenAI + ElevenLabs
└── mobile/           # Flutter Android app
```

---

## Backend Setup

### Requirements

- Python 3.11+
- OpenAI API key (GPT-4o-mini)
- ElevenLabs API key

### Install

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
SECRET_KEY=your-super-secret-key-change-this
DATABASE_URL=sqlite:///./storycast.db
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
STORAGE_PATH=./storage
OPENAI_MODEL=gpt-4o-mini
```

### Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs available at: http://localhost:8000/docs

### API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Login, get JWT token |
| GET  | `/api/v1/auth/me` | Current user info |
| GET  | `/api/v1/books` | List user's books |
| POST | `/api/v1/books` | Upload book (PDF/EPUB/DOCX/TXT) |
| GET  | `/api/v1/books/{id}/status` | Processing status + progress |
| GET  | `/api/v1/books/{id}/characters` | List characters with voices |
| PUT  | `/api/v1/books/{id}/characters/{char_id}` | Edit character/voice |
| GET  | `/api/v1/voices/available` | Available ElevenLabs voices |
| GET  | `/api/v1/books/{id}/segments` | All audio segments |
| GET  | `/api/v1/books/{id}/segments/{index}/audio` | Stream audio (JWT required) |
| GET  | `/api/v1/books/{id}/player-state` | Saved playback position |
| PUT  | `/api/v1/books/{id}/player-state` | Save playback position |
| POST | `/api/v1/bookmarks` | Create bookmark |
| GET  | `/api/v1/books/{id}/bookmarks` | List bookmarks |
| DELETE | `/api/v1/bookmarks/{id}` | Delete bookmark |

### Processing Pipeline

1. **Upload** — file saved, background thread spawned (returns `201` immediately)
2. **Extract** — text extracted from PDF/EPUB/DOCX/TXT, split into ~500-char segments
3. **Analyze** — GPT-4o-mini identifies characters and assigns voices
4. **TTS** — ElevenLabs generates audio for each segment with emotion-aware parameters
5. **Ready** — progress reaches 100%, app notified via status polling

---

## Android App Setup

### Requirements

- Flutter 3.19+  (`flutter --version`)
- Android SDK 21+ (Android 5.0)
- A physical Android device or emulator

### Configure backend URL

Edit `mobile/lib/core/constants/app_constants.dart`:

```dart
// For Android emulator (default):
static const String baseUrl = 'http://10.0.2.2:8000/api/v1';

// For physical device (use your machine's local IP):
static const String baseUrl = 'http://192.168.1.X:8000/api/v1';
```

### Install dependencies

```bash
cd mobile
flutter pub get
```

### Run on emulator / device

```bash
flutter run
```

### Build installable APK

```bash
cd mobile
flutter build apk --release
```

APK location: `mobile/build/app/outputs/flutter-apk/app-release.apk`

Transfer to your device and install (allow "Install from unknown sources" in device settings).

### Build split APKs (smaller file, recommended)

```bash
flutter build apk --split-per-abi
```

This produces three APKs optimized per CPU architecture:
- `app-armeabi-v7a-release.apk` — older 32-bit devices
- `app-arm64-v8a-release.apk` — modern 64-bit devices ✓ (most common)
- `app-x86_64-release.apk` — emulators

---

## First-time Usage

1. Start the backend server
2. Install the APK on your Android device
3. Register an account in the app
4. Tap **+** to upload a book (PDF, EPUB, DOCX, or TXT)
5. Wait for AI processing (progress bar shown in real time)
6. Review and customize character voices on the Characters screen
7. Tap **Play** — enjoy your cinematic audiobook

---

## Supported Emotions

The TTS engine maps narrative emotion to ElevenLabs voice parameters:

| Emotion | Description |
|---------|-------------|
| neutral | Standard narration |
| happy | Bright, upbeat tone |
| sad | Slow, subdued |
| angry | Intense, clipped |
| fearful | Tense, whispery |
| surprised | High energy, fast |
| romantic | Warm, intimate |
| suspenseful | Low, deliberate |

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✓ | — | JWT signing secret (use a long random string) |
| `DATABASE_URL` | — | `sqlite:///./storycast.db` | SQLAlchemy DB URL |
| `OPENAI_API_KEY` | ✓ | — | OpenAI API key |
| `ELEVENLABS_API_KEY` | ✓ | — | ElevenLabs API key |
| `STORAGE_PATH` | — | `./storage` | Directory for audio files |
| `OPENAI_MODEL` | — | `gpt-4o-mini` | OpenAI model for analysis |
| `MAX_FILE_SIZE_MB` | — | `100` | Upload size limit |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | `10080` | JWT expiry (7 days) |

---

## Troubleshooting

**App can't connect to backend on physical device**
→ Set `baseUrl` in `app_constants.dart` to your machine's LAN IP (e.g. `192.168.1.10`), not `10.0.2.2` (that's emulator-only).

**"OPENAI_API_KEY não configurada"**
→ Check your `.env` file is in the `backend/` directory and the key is set.

**Processing stuck at 0%**
→ Check the backend logs. Usually an invalid API key or network error.

**Audio won't play**
→ Ensure the backend is running and reachable. Audio segments stream directly from the backend with JWT auth headers.

**APK install blocked**
→ On Android: Settings → Security → Install unknown apps → allow your browser or file manager.
