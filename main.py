"""
Meeting Summarizer - Backend (Gemini version)
-----------------------------------------------
Flow:
1. User uploads an audio file (/upload)
2. Audio is sent directly to Gemini (it can listen to audio natively) along
   with a prompt asking for a transcript + structured summary
3. Gemini's response is parsed into transcript / summary / decisions / action items
4. Result is stored in SQLite and returned to the caller.

Only needs ONE API key: GEMINI_API_KEY (free tier available, no card needed).
Get one at: https://aistudio.google.com/apikey

Run with:
    uvicorn main:app --reload --port 8000
"""

import os
import json
import sqlite3
import tempfile
from datetime import datetime, timezone

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("WARNING: Missing GEMINI_API_KEY in environment (.env file).")

client = genai.Client(api_key=GEMINI_API_KEY)

# Free-tier model with native audio understanding.
MODEL_NAME = "gemini-3.6-flash"

DB_PATH = os.path.join(os.path.dirname(__file__), "meetings.db")

app = FastAPI(title="Meeting Summarizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            transcript TEXT,
            summary TEXT,
            decisions TEXT,
            action_items TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


PROMPT = """You are an assistant that transcribes and summarizes meeting audio.

Listen to the attached audio and return ONLY a valid JSON object (no markdown
fences, no extra commentary before or after) with exactly these keys:

- "transcript": the full verbatim transcript of the audio, as plain text
- "summary": a concise 3-6 sentence overview of what the meeting was about
- "decisions": a list of key decisions that were made (strings). Empty list if none.
- "action_items": a list of objects, each with "task" (string) and "owner"
  (string, use "Unassigned" if no owner is mentioned)

Respond with ONLY the JSON object, nothing else.
"""


MIME_TYPES = {
    ".mp3": "audio/mp3",
    ".mpga": "audio/mpeg",
    ".mpeg": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".webm": "audio/webm",
}


def transcribe_and_summarize(file_path: str, mime_type: str) -> dict:
    """Upload the audio to Gemini and get back transcript + structured summary."""
    uploaded_file = client.files.upload(path=file_path)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[uploaded_file, PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    raw_text = (response.text or "").strip()
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back gracefully so the API never hard-crashes on a malformed response
        parsed = {
            "transcript": raw_text,
            "summary": "Could not parse structured summary — see raw transcript.",
            "decisions": [],
            "action_items": [],
        }

    return parsed


@app.post("/upload")
async def upload_meeting(file: UploadFile = File(...)):
    """Accept an audio file, transcribe + summarize it via Gemini, store it, return result."""

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {list(MIME_TYPES.keys())}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = transcribe_and_summarize(tmp_path, MIME_TYPES[ext])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        os.remove(tmp_path)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """
        INSERT INTO meetings (filename, transcript, summary, decisions, action_items, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            file.filename,
            result.get("transcript", ""),
            result.get("summary", ""),
            json.dumps(result.get("decisions", [])),
            json.dumps(result.get("action_items", [])),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    meeting_id = cursor.lastrowid
    conn.close()

    return {
        "id": meeting_id,
        "filename": file.filename,
        "transcript": result.get("transcript", ""),
        "summary": result.get("summary", ""),
        "decisions": result.get("decisions", []),
        "action_items": result.get("action_items", []),
    }


@app.get("/meetings")
def list_meetings():
    """Return all past meetings (id, filename, summary, date) for a history view."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, filename, summary, created_at FROM meetings ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "filename": r[1], "summary": r[2], "created_at": r[3]}
        for r in rows
    ]


@app.get("/meetings/{meeting_id}")
def get_meeting(meeting_id: int):
    """Return full detail (transcript, summary, decisions, action items) for one meeting."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, filename, transcript, summary, decisions, action_items, created_at "
        "FROM meetings WHERE id = ?",
        (meeting_id,),
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return {
        "id": row[0],
        "filename": row[1],
        "transcript": row[2],
        "summary": row[3],
        "decisions": json.loads(row[4]),
        "action_items": json.loads(row[5]),
        "created_at": row[6],
    }


@app.get("/")
def root():
    return {"status": "Meeting Summarizer API is running (Gemini)"}
