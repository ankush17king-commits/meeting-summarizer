# Meeting Summarizer

Upload a meeting audio recording → get a transcript, a summary, key decisions,
and action items with owners.

## Stack

- **Transcription + Summarization:** Google Gemini API (`gemini-2.5-flash`) —
  one model does both in a single call, using its native audio understanding
- **Backend:** FastAPI (Python) + SQLite (stores past meetings)
- **Frontend:** Plain HTML/JS (no build step needed)

Gemini's free tier (Flash models) works for this without adding a credit card —
that's why it's used instead of OpenAI/Anthropic here.

## Project structure

```
meeting-summarizer/
├── backend/
│   ├── main.py           # FastAPI app: /upload, /meetings, /meetings/{id}
│   ├── requirements.txt
│   └── .env.example      # copy to .env and add your API key
├── frontend/
│   └── index.html        # upload UI, just open in a browser
└── README.md
```

## Setup (do this once)

### 1. Get a free Gemini API key
Go to https://aistudio.google.com/apikey, sign in with a Google account,
click "Create API key". No credit card required for the free tier.

Free tier limits (subject to change, check the AI Studio page): a handful of
requests per minute and up to ~1,000 requests/day on Flash models — more than
enough for building and demoing this project.

### 2. Install Python dependencies
```bash
cd meeting-summarizer/backend
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add your API key
```bash
cp .env.example .env
```
Open `.env` and paste in your real key:
```
GEMINI_API_KEY=AIza...
```

## Running it

### 1. Start the backend
```bash
cd meeting-summarizer/backend
uvicorn main:app --reload --port 8000
```
Leave this running. You should see `Uvicorn running on http://127.0.0.1:8000`.

Sanity-check by opening http://localhost:8000 in a browser — you should see
`{"status": "Meeting Summarizer API is running (Gemini)"}`.

### 2. Open the frontend
Just open `frontend/index.html` directly in your browser (double-click it, or
right-click → Open With → your browser). No server needed for the frontend.

### 3. Use it
1. Click the upload box (or drag a file in) and choose an audio file
   (`.mp3`, `.wav`, `.m4a`, `.mp4`, `.webm`, `.mpeg`, `.mpga`)
2. Click **Transcribe & summarize**
3. Wait — usually 15–60 seconds depending on the length of the recording
4. Review the summary, decisions, action items (with owners), and full transcript

## API endpoints (for reference / testing with curl or Postman)

| Method | Endpoint             | Description                                  |
|--------|-----------------------|-----------------------------------------------|
| POST   | `/upload`             | Upload audio, get transcript + summary back  |
| GET    | `/meetings`           | List all past meetings (id, filename, summary)|
| GET    | `/meetings/{id}`      | Get full detail for one past meeting          |

Example curl test:
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/your/meeting.mp3"
```

## How the prompt works

The backend sends the audio file directly to Gemini (it listens to audio
natively — no separate ASR step) along with a prompt asking it to return a
JSON object with `transcript`, `summary`, `decisions`, and `action_items`.
See the `PROMPT` variable in `main.py` if you want to tweak it — e.g. ask it
to also tag priority level, detect speaker names, or flag unresolved questions.

## Things to check before you submit / demo

- [ ] Test with at least 2–3 real meeting recordings of different lengths
- [ ] Confirm transcription accuracy is reasonable (accents, overlapping
      speakers, or poor audio quality can reduce accuracy — mention this as
      a known limitation if it comes up)
- [ ] Confirm action items correctly extract an owner when one is stated
- [ ] Record a short demo video: show uploading a file, waiting, and the
      final output (screen recording tools: OBS Studio, Loom, or QuickTime
      on Mac)
- [ ] Write final commit + push to GitHub with this README included
- [ ] Double check `.env` is in `.gitignore` so you don't leak your API key!

## Notes / possible extensions (optional, if you want to go further)

- Add speaker diarization — ask Gemini to label speakers in the prompt
  (it can often do this directly from audio)
- Add a "history" page in the frontend using the existing `/meetings` endpoint
- Add authentication if this needs to be multi-user
- If you later want higher rate limits or SLAs, Gemini's paid tier or
  Vertex AI are drop-in upgrades from the same SDK
# meeting-summarizer
