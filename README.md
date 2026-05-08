# VoiceOps AI — Real-Time Emergency Response Pipeline

A real-time voice emergency intake pipeline. Callers record audio in the browser, which is transcribed, analyzed by AI, stored as a structured incident in Azure Cosmos DB, and responded to with a synthesized voice reply. A dispatcher dashboard allows filtering and status management of all incidents.

---

## Architecture

```
/backend/                    FastAPI Python backend
/emergency-voice-frontend/   Next.js frontend (React 19, Tailwind, TypeScript)
```

**Azure services:**
- **Azure Cognitive Services Speech** — Speech-to-Text (STT) + Text-to-Speech (TTS)
- **Azure OpenAI** — Incident extraction + emergency response generation
- **Azure Cosmos DB** — Session/incident storage and retrieval
- **Azure Maps** — Geocoding, nearby resource search, interactive incident map

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Azure account with Speech, OpenAI, Cosmos DB, and Maps resources provisioned
- Create `backend/.env` with your Azure credentials (see `.env` variable names below)

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

### Required Environment Variables (`backend/.env`)

```
AZURE_SPEECH_KEY=
REGION=
AZURE_OPENAI_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=
AZURE_OPENAI_DEPLOYMENT=
AZURE_COSMOS_ENDPOINT=
AZURE_COSMOS_KEY=
AZURE_COSMOS_DATABASE=
AZURE_COSMOS_CONTAINER=
AZURE_MAPS_KEY=
```

Frontend also requires `NEXT_PUBLIC_AZURE_MAPS_KEY` in `emergency-voice-frontend/.env.local`.

---

## How It Works

1. **Start Session** — User clicks "Start New Session"; a session document is created in Cosmos DB
2. **Record** — Click the mic button to start recording; click again to stop and auto-send
3. **Transcribe** — Backend converts the browser WebM audio to PCM WAV via FFmpeg, then sends to Azure Speech-to-Text
4. **Extract** — Azure OpenAI parses the transcript into a structured incident (type, severity, location, injuries, etc.), using already-collected fields as context so it never re-asks
5. **Enrich** — Location string is geocoded via Azure Maps; nearby hospitals, fire stations, and police are fetched within 5 km
6. **Store** — Session document is upserted to Cosmos DB with all enriched fields
7. **Respond** — Azure OpenAI generates a calm, directive follow-up question or summary (max 5 turns); Azure TTS converts it to audio
8. **Play** — Frontend displays transcript, incident details, and auto-plays the AI audio response
9. **Map** — An interactive Azure Maps view shows the incident location and nearby resources
10. **End Session** — Session ends manually, or automatically after 60 seconds of inactivity

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/sessions/start` | Create a new session/incident in Cosmos DB |
| POST | `/sessions/{session_id}/voice-intake` | Full pipeline: audio → transcript → incident → TTS |
| GET | `/sessions/{session_id}/end` | End session (GET variant) |
| POST | `/sessions/{session_id}/end/` | End session (POST variant, used by idle timer) |
| GET | `/incidents` | Fetch 20 most recent incidents |
| GET | `/incidents/filter` | Filter by `?status=` and/or `?severity=` |
| PUT | `/incidents/{incident_id}` | Update incident status via `?status=` |

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
│   ├── main.py                  # FastAPI app, session lifecycle, audio pipeline
│   ├── incident_extractor.py    # Context-aware structured extraction via Azure OpenAI
│   ├── location_enrichment.py   # Azure Maps geocoding (location string → lat/lng)
│   ├── nearby_resources.py      # Azure Maps POI search (hospitals, fire, police)
│   ├── schemas.py               # Pydantic data models
│   └── requirements.txt         # Python dependencies
│
├── emergency-voice-frontend/
│   ├── app/
│   │   ├── page.tsx             # Voice intake — session, mic, transcript, map
│   │   ├── incidents/page.tsx   # Dispatcher dashboard
│   │   └── layout.tsx           # Root layout
│   ├── components/
│   │   └── IncidentMap.tsx      # Azure Maps component (dynamic import, SSR-safe)
│   └── package.json
│
├── CLAUDE.md                    # Developer reference (architecture, conventions)
└── README.md
```
