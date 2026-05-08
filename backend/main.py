import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import azure.cognitiveservices.speech as speechsdk
from fastapi import FastAPI, UploadFile, File, HTTPException
from dotenv import load_dotenv
from openai import AzureOpenAI
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import imageio_ffmpeg
import base64
from incident_extractor import extract_incident_details
from azure.cosmos import CosmosClient, PartitionKey
from azure.core.exceptions import AzureError
from location_enrichment import geocode_location
from nearby_resources import find_nearby_resources


load_dotenv(Path(__file__).parent/".env")
app = FastAPI()
session: dict = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "https://voice-ops-ai-real-time-emergency-re.vercel.app"
        ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("REGION")

client = AzureOpenAI(
    api_key= os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

cosmos_client = CosmosClient(
     url = os.getenv("AZURE_COSMOS_ENDPOINT"),
     credential = os.getenv("AZURE_COSMOS_KEY")
)

database = cosmos_client.get_database_client(os.getenv("AZURE_COSMOS_DATABASE"))
container = database.get_container_client(os.getenv("AZURE_COSMOS_CONTAINER"))

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def merge_incident_update(existing_incident:dict, new_data:dict, transcript:str):
    now = utc_now()
    
    existing_incident.setdefault("transcript_history", [])
    existing_incident["transcript_history"].append({
         "text": transcript,
         "ai_response": None,
         "created_at": now
    })
    print(existing_incident)
    scalar_fields = ["emergency_type", "severity", "location", "callback_number", "summary"]
    for field in scalar_fields:
        value = new_data.get(field)
        if value not in [None, "", "unknown", "Unknown", "UNKNOWN"]:
            existing_incident[field] = value

    # Only update injuries when the new value adds information (True always wins; False only sets if still unknown)
    new_injuries = new_data.get("injuries")
    if new_injuries is True or (new_injuries is False and existing_incident.get("injuries") is None):
        existing_incident["injuries"] = new_injuries

    # Case-insensitive keyword fallback for emergency type
    emergencies = ['medical', 'fire', 'crime', 'accident', 'natural_disaster']
    import re
    transcript_words = set(re.findall(r'\b\w+\b', transcript.lower()))
    matched = [e for e in emergencies if e in transcript_words]
    if matched:
        existing_incident['emergency_type'] = matched[0]
    # print("existing_incident", existing_incident)
    old_symptoms = existing_incident.get("symptoms") or []
    new_symptoms = new_data.get("symptoms") or []

    existing_incident["symptoms"] = list(set(old_symptoms + new_symptoms))

    required_fields = [
        "emergency_type",
        "severity",
        "callback_number",
        "location"
    ]

    existing_incident["missing_fields"] =[
        field for field in required_fields
        if not existing_incident.get(field)  
    ]

    existing_incident["updated_at"] = now


    if len(existing_incident["missing_fields"]) == 0:
        existing_incident["resolved"] = True
    else:
        existing_incident["resolved"] = False

    return  existing_incident

def get_session_by_id(session_id:str):
     if session_id in session:
          return session[session_id]

     query = "Select * from c where c.session_id = @session_id"
     items = list(container.query_items(
          query = query,
          parameters=[{
               "name":"@session_id", "value": session_id}],
          enable_cross_partition_query=True
     ))

     if not items:
          raise HTTPException(status_code=404, detail="Session Not Found")
     return items[0]


@app.post("/sessions/start")
def start_session():
    now = utc_now()
    session_id = f"SESSION-{uuid4().hex[:8].upper()}"

    session_doc = {
        "id": session_id,
        "session_id": session_id,
        "session_status": "active",
        "status": "new",
        "resolved": False,
        "transcript_history": [],
        "emergency_type": None,
        "severity": None,
        "location": None,
        "injuries": None,
        "symptoms": [],
        "callback_number": None,
        "summary": None,
        "missing_fields": [
            "emergency_type",
            "location",
            "severity",
            "callback_number"
        ],
        "created_at": now,
        "updated_at": now,
        "ended_at": None
    }

    container.create_item(session_doc)

    return session_doc

@app.get("/sessions/{session_id}/end")
def end_session(session_id:str):
     try:
          existing_incident = get_session_by_id(session_id)
          existing_incident["session_status"] = "ended"
          existing_incident["status"] = "closed"
          existing_incident["ended_at"] = utc_now()
          existing_incident["updated_at"] = utc_now()

          container.upsert_item(existing_incident)
          return existing_incident
     except Exception as e:
          raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")

@app.get("/")
def root():
    return {"status": "ok", "service":"voiceops-backend"}


@app.post("/sessions/{session_id}/voice-intake")
async def voice_intake(session_id:str, file: UploadFile = File(...)):
    temp_path = None
    try:
        existing_incident = get_session_by_id(session_id)
        print(existing_incident)

        if existing_incident.get("session_status") == "ended":
            return {
                "error": "This session has ended. No further updates are allowed."
            }
        
        content = await file.read()
        suffix = ".webm" if file.content_type and "webm" in file.content_type else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_raw:
            temp_raw.write(content)
            temp_raw_path = temp_raw.name

        # Convert to WAV (PCM 16kHz mono) for Azure Speech SDK
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
            temp_path = temp_wav.name
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg_bin, "-y", "-i", temp_raw_path, "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", temp_path],
            check=True, capture_output=True
        )
        os.remove(temp_raw_path)

        # 2. Azure Speech-to-Text
        speech_config = speechsdk.SpeechConfig(
                subscription=SPEECH_KEY,
                region=SPEECH_REGION
            )

        audio_config_stt = speechsdk.AudioConfig(filename=temp_path)
        recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config_stt
            )
        print("Transcribing with Azure...")
        result = recognizer.recognize_once_async().get()

        # Release SDK objects immediately so Windows unlocks the file
        recognizer = None
        audio_config_stt = None

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                transcript = result.text
        else:
                transcript = ""
                print(f"Speech Recognition failed: {result.reason}")

        # Temp WAV no longer needed — delete before any early returns
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except PermissionError:
                pass
        temp_path = None

        # 3. Azure OpenAI Call
        if not transcript:
            return {"transcript": "No speech detected", "ai_response": "I couldn't hear you. Please try again."}
        print(f"Transcript:{transcript}")

        incident = extract_incident_details(transcript, existing_incident)
        
        new_data = incident.model_dump()
       
        incident_dict = merge_incident_update(
             existing_incident=existing_incident,
             new_data=new_data,
             transcript=transcript,
        )
       
        if incident_dict.get("location"):
            location_enrichment = geocode_location(incident_dict["location"])

            if location_enrichment:
                incident_dict["location_enrichment"] = location_enrichment
                if location_enrichment.get("latitude") and location_enrichment.get("longitude"):
                    emergency_type = incident_dict.get("emergency_type") or incident_dict.get("detected_emergency_type")

                    nearby_resources = find_nearby_resources(
                        latitude = location_enrichment["latitude"],
                        longitude = location_enrichment["longitude"],
                        emergency_type=emergency_type
                    )

                    incident_dict["nearby_resources"] = nearby_resources
        
        session[session_id] = incident_dict
        
        container.upsert_item(incident_dict)

        # Build conversation history from previous turns
        history = incident_dict.get("transcript_history", [])
        conversation_messages = []

        for turn in history[:-1]:  # all turns except the current one
            conversation_messages.append({"role": "user", "content": turn["text"]})
        
            if turn.get("ai_response"):
                conversation_messages.append({"role": "assistant", "content": turn["ai_response"]})
        # Agent should ask upto 5 clarifying questions
        MAX_TURNS = 5
        turns_completed = len(incident_dict.get("transcript_history", []))
        if turns_completed >= MAX_TURNS:
            question_instruction = (
                "You have reached the maximum number of exchanges. "
                "Do NOT ask any more questions. "
                "Summarize all collected information and calmly close the intake."
            )
        else:
            remaining = MAX_TURNS - turns_completed
            question_instruction = (
                f"You have {remaining} exchange(s) remaining (max {MAX_TURNS} total). "
                "Ask ONE short question to collect the next missing field. "
                "If missing_fields is empty, summarize the emergency calmly and say intake is complete."
            )

        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                messages=[
                    {
                        "role":"system",
                        "content":"""
                        You are an emergency intake assistant.
                        Collect location, emergency type, severity, injuries, and caller callback number.
                        Do not claim emergency services are dispatched unless confirmed by backend.
                        If life-threatening, tell caller to call 911 immediately.

                        Safety rules:
                            - Do not claim responders have been dispatched.
                            - If life-threatening, tell the caller to call 911 immediately.
                            - Ask only one follow-up question at a time.
                            - Keep your response under 2 sentences.
                            - Do not repeat your questions.
                            - If user responds with all the essential details, do not ask additional questions.
                            - Stay calm, direct, and supportive.
                            """
                    },
                    *conversation_messages,
                    {
                        "role":"user",
                        "content": f"""
                    Latest caller message: {transcript}

                    Already collected (DO NOT ask about these again):
                    - Emergency type: {incident_dict.get('emergency_type') or 'not yet known'}
                    - Location: {incident_dict.get('location') or 'not yet known'}
                    - Severity: {incident_dict.get('severity') or 'not yet known'}
                    - Injuries: {incident_dict.get('injuries') or 'not yet known'}
                    - Callback number: {incident_dict.get('callback_number') or 'not yet known'}

                    Still missing: {incident_dict.get('missing_fields', [])}

                    {question_instruction}
                    """
                    }
                ],
                temperature = 0.3,
            )
        
        ai_response = response.choices[0].message.content

        # Store AI response in the last transcript history entry
        incident_dict["transcript_history"][-1]["ai_response"] = ai_response
        session[session_id] = incident_dict
        container.upsert_item(incident_dict)

        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
        audio_output_path = "response.wav"
        audio_config_tts= speechsdk.audio.AudioOutputConfig(filename=audio_output_path)
        
        synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config_tts
            )
            
        synthesizer.speak_text_async(ai_response).get()
        with open(audio_output_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        return{  "session_id":session_id,
                "transcript":transcript,
                "ai_response":ai_response,
                "incident": incident_dict,
                "resolved":incident_dict.get("resolved", False),
                "audio_b64":audio_b64
            }
    except Exception as e:
        print(f"Critical Error:{str(e)}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except PermissionError:
                pass
        return {"error": str(e)}, 500

@app.get("/incidents")
def get_incidents():
    
    query = "Select * from c Order by c.created_at desc offset 0 limit 20"

    items = list(
         container.query_items(
              query=query,
              enable_cross_partition_query=True
         )
    )
    return items

@app.get("/incidents/filter")
def filter_incidents(status:str=None, severity:str=None):
     query = "SELECT * from c where 1=1"

     if status:
          query += f" AND c.status='{status}'"
     if severity:
          query += f" AND c.severity='{severity}'"
     items = list(
          container.query_items(
               query=query,
               enable_cross_partition_query=True
          )
     )
     return items

@app.put("/incidents/{incident_id}")
def update_incident(incident_id:str, status:str):
     query = f"select * from c where c.incident_id='{incident_id}'"
     items = list(container.query_items(query=query, enable_cross_partition_query=True))
     print(items)
     if not items:
          return{"error": "Not found"}
     item = items[0]
     item["status"] = status
     container.upsert_item(item)

     return item
