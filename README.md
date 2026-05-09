# VoiceOps AI — Real-Time Emergency Response Pipeline

A real-time voice emergency intake pipeline. Callers record audio in the browser, which is transcribed, analyzed by AI, stored as a structured incident in Azure Cosmos DB, and responded to with a synthesized voice reply. A dispatcher dashboard allows filtering and status management of all incidents.

**Live Demo:**
- Demo Video: https://www.loom.com/share/8e611695924141dcbea6c88c074293e0
- Frontend: [https://voice-ops-ai-real-time-emergency-re.vercel.app/](https://voice-ops-ai-real-time-emergency-re.vercel.app/)
- Backend API: hosted on Render

<img width="1807" height="953" alt="image" src="https://github.com/user-attachments/assets/1efe8b30-1781-4f02-b62a-6ddcd378917e" />
<img width="1577" height="804" alt="image" src="https://github.com/user-attachments/assets/33cf1f07-d6a5-4fb0-99b5-96c67f57532a" />
<img width="1573" height="934" alt="image" src="https://github.com/user-attachments/assets/cd10d28f-580e-4ff3-9b7d-1a0c3fc90eca" />
<img width="1823" height="619" alt="image" src="https://github.com/user-attachments/assets/8df9ac5c-6b9f-4f84-a78a-a3b34fba1853" />
<img width="1869" height="549" alt="image" src="https://github.com/user-attachments/assets/3fd91281-1249-4f6a-9639-ef3cedf9b499" />
<img width="1589" height="950" alt="image" src="https://github.com/user-attachments/assets/9af6997d-5ac8-4c25-ada5-7310461eb2ff" />



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

## How to Use

1. Open the [live app](https://voice-ops-ai-real-time-emergency-re.vercel.app/)
2. Click **Start New Session** to begin
3. Click the **microphone button** to start recording your emergency
4. Click the microphone button again to stop — the audio is automatically sent for processing
5. The AI will respond with a follow-up question and speak the reply aloud
6. Continue recording to provide additional details across multiple turns
7. The session ends automatically after **60 seconds of inactivity**, or click **End Session** manually
8. Once a location is detected, an interactive map shows the incident location and nearby resources (hospitals, fire stations, police)

---

## How It Works

1. **Start Session** — A session document is created in Cosmos DB
2. **Record** — Click the mic button to start; click again to stop and auto-send
3. **Transcribe** — Backend converts the audio to WAV via FFmpeg, then sends to Azure Speech-to-Text
4. **Extract** — Azure OpenAI parses the transcript into a structured incident (type, severity, location, injuries, etc.), using already-collected fields as context so it never re-asks
5. **Enrich** — Location string is geocoded via Azure Maps; nearby hospitals, fire stations, and police are fetched within 5 km
6. **Store** — Session document is upserted to Cosmos DB with all enriched fields
7. **Respond** — Azure OpenAI generates a calm follow-up question or summary (max 5 turns); Azure TTS converts it to audio
8. **Map** — An interactive Azure Maps view shows the incident location and nearby resources
9. **End Session** — Ends manually or automatically after 60 seconds of inactivity

---

## Running Locally

### Prerequisites
- Python 3.10+
- Node.js 18+
- Azure account with Speech, OpenAI, Cosmos DB, and Maps resources provisioned

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

> Environment variables for Azure credentials must be configured in `backend/.env` and `emergency-voice-frontend/.env.local` before running locally.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/sessions/start` | Create a new session/incident in Cosmos DB |
| POST | `/sessions/{session_id}/voice-intake` | Full pipeline: audio → transcript → incident → TTS |
| GET | `/sessions/{session_id}/end` | End session |
| GET | `/incidents` | Fetch 20 most recent incidents |
| GET | `/incidents/filter` | Filter by `?status=` and/or `?severity=` |
| PUT | `/incidents/{incident_id}` | Update incident status via `?status=` |

---

## Dispatcher Dashboard

Navigate to `/incidents` to view the dispatcher dashboard:

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
│   ├── Dockerfile               # Docker config for Render deployment
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
