# VoiceOps AI — Real-Time Emergency Response Pipeline

A real-time voice emergency intake pipeline. Callers record an audio message in the browser, which is transcribed, analyzed by AI, stored as a structured incident in Azure Cosmos DB, and responded to with a synthesized voice reply. A dispatcher dashboard allows filtering and status management of all incidents.

---

## Architecture

```
/backend/                    FastAPI Python backend
/emergency-voice-frontend/   Next.js React frontend
```

**Azure services:**
- **Azure Cognitive Services Speech** — Speech-to-Text (STT) + Text-to-Speech (TTS)
- **Azure OpenAI** — Incident extraction + emergency response generation
- **Azure Cosmos DB** — Incident storage and retrieval

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Azure account with Speech, OpenAI, and Cosmos DB resources provisioned
- Create `backend/.env` with your Azure credentials (see CLAUDE.md for the required variable names)

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Server runs on `http://localhost:8000`

### Frontend

```bash
cd emergency-voice-frontend
npm install
npm run dev
```

App runs on `http://localhost:3000`

---

## How It Works

1. **Record** — User clicks "Start Recording" in the browser; clicking "Stop Recording" automatically sends the audio
2. **Transcribe** — Backend converts the audio to PCM WAV via FFmpeg, then sends it to Azure Speech-to-Text
3. **Extract** — Azure OpenAI parses the transcript into a structured incident (type, severity, location, injuries, etc.)
4. **Store** — Incident is saved to Azure Cosmos DB with a generated ID and timestamp
5. **Respond** — Azure OpenAI generates a calm, directive emergency response; Azure TTS converts it to audio
6. **Play** — Frontend displays the transcript, incident details, and auto-plays the AI audio response

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/voice-intake` | Full pipeline: audio → transcript → incident → TTS response |
| GET | `/incidents` | Fetch 20 most recent incidents |
| GET | `/incidents/filter` | Filter by `?status=` and/or `?severity=` |
| PUT | `/incidents/{id}` | Update incident status |

---

## Dispatcher Dashboard

Navigate to `http://localhost:3000/incidents` to view the incident dashboard:

- View all incoming incidents with severity and status badges
- Filter by status (`new`, `in_review`, `escalated`, `closed`) and severity
- Update incident status with one click
- Auto-refreshes every 5 seconds

---

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI app and all endpoints
│   ├── incident_extractor.py    # Structured extraction via Azure OpenAI
│   ├── schemas.py               # Pydantic data models
│   └── requirements.txt         # Python dependencies
│
├── emergency-voice-frontend/
│   ├── app/
│   │   ├── page.tsx             # Voice intake page
│   │   ├── incidents/page.tsx   # Dispatcher dashboard
│   │   └── layout.tsx           # Root layout
│   └── package.json
│
├── CLAUDE.md                    # Developer reference (architecture, conventions)
└── README.md
```
