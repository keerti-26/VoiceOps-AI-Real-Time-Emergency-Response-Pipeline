import os
import json
from openai import AzureOpenAI
from dotenv import load_dotenv
from pathlib import Path
from schemas import IncidentExtraction

load_dotenv(Path(__file__).parent/".env")

client = AzureOpenAI(
    api_key= os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

def extract_incident_details(transcript:str)-> IncidentExtraction:
    response = client.chat.completions.create(
        model = DEPLOYMENT,
        messages = [
            {
                "role": "system",
                "content": """
             You extract structured emergency incident details from caller transcripts.

             Return only valid JSON with no markdown, no code fences, just raw JSON:
             {
                "emergency_type": "medical | fire | crime | accident | natural_disaster | Other | unknown",
                "severity": "low | medium | high | critical | unknown",
                "location": string or null,
                "injuries": true or false,
                "symptoms": array of strings,
                "callback_number": string or null,
                "summary": string,
                "missing_fields": array of strings
             }

             Rules:
             - Do not invent missing details.
             - If location is incomplete, include "location" in missing_fields.
             - If callback number is missing, include "callback_number" in missing_fields.
             - Use critical for life-threatening situations like chest pain, unconsciousness, fire, active violence, severe bleeding.

            """
            },
            {
               "role":"user",
               "content":transcript
            }
        ],
        temperature = 0.1
    )
    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    parsed = json.loads(content)
    return IncidentExtraction(**parsed)
