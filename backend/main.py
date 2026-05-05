import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import azure.cognitiveservices.speech as speechsdk
from fastapi import FastAPI, UploadFile, File
from dotenv import load_dotenv
from openai import AzureOpenAI
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import imageio_ffmpeg
import base64
from incident_extractor import extract_incident_details
from azure.cosmos import CosmosClient, PartitionKey
from azure.core.exceptions import AzureError


load_dotenv(Path(__file__).parent/".env")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

@app.get("/")
def home():
    return {"status": "Voice Emergency Pipeline is running"}


@app.post("/voice-intake")
async def voice_intake(file: UploadFile = File(...)):
    temp_path = None
    try:
        content = await file.read()
        suffix = ".webm" if file.content_type and "webm" in file.content_type else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_raw:
            temp_raw.write(content)
            temp_raw_path = temp_raw.name
        print(temp_raw_path)

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
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                transcript = result.text
        else:
                transcript = ""
                print(f"Speech Recognition failed: {result.reason}")


        # 3. Azure OpenAI Call
        if not transcript:
            return {"transcript": "No speech detected", "ai_response": "I couldn't hear you. Please try again."}
        print(f"Transcript:{transcript}")

        incident = extract_incident_details(transcript)
        
        incident_dict = incident.model_dump()
        inc_id = f"INC-{uuid4().hex[:8].upper()}"

        incident_dict["id"] = inc_id
        incident_dict["incident_id"] = inc_id
        incident_dict["status"] = "new"
        incident_dict["created_at"] = datetime.now(timezone.utc).isoformat()

        container.create_item(incident_dict)

        print(incident_dict)

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
                            - Stay calm, direct, and supportive.
                            """
                    },
                    {
                        "role":"user",
                        "content": transcript
                    }
                ],
                temperature = 0.3
            )
        
        ai_response = response.choices[0].message.content

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

        return{
                "transcript":transcript,
                "ai_response":ai_response,
                "incident": incident_dict,
                "audio_b64":audio_b64
            }
    except Exception as e:
        print(f"Critical Error:{str(e)}")
        if temp_path and os.path.exists(temp_path):
             os.remove(temp_path)
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
