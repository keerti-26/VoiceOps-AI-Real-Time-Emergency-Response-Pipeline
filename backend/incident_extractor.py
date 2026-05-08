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

def extract_incident_details(transcript: str, existing_incident: dict = None) -> IncidentExtraction:
    already_known = ""
    if existing_incident:
        parts = []
        # counter = counter+1
        for field, label in [
            ("emergency_type", "Emergency type"),
            ("location", "Location"),
            ("severity", "Severity"),
            ("callback_number", "Callback number"),
            ("injuries", "Injuries reported"),
        ]:
            val = existing_incident.get(field)
            if val is not None and str(val).lower() not in ["unknown", "", "none"]:
                parts.append(f"- {label}: {val}")
        if parts:
            already_known = (
                "\n\nAlready known from earlier in this session (do NOT include these in missing_fields):\n"
                + "\n".join(parts)
            )
    print(already_known)
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
             - If any keyword appears in the transcript (medical, fire, crime, accident, natural_disaster) use it as emergency_type.
             - Only add a field to missing_fields if it is genuinely absent from ALL context, including already-known values provided below.
             - Never add already-known fields to missing_fields.
             - If location is incomplete or absent, include "location" in missing_fields.
             - If callback number is missing, include "callback_number" in missing_fields.
             - Use critical for life-threatening situations like chest pain, unconsciousness, fire, active violence, severe bleeding.
            """
            },
            {
               "role": "user",
               "content": f"Latest caller message: {transcript}{already_known}"
            }
        ],
        temperature = 0.1
    )
    content = response.choices[0].message.content.strip()
    # print("content:", content)
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    parsed = json.loads(content)
    # print("parsed:", parsed)
    return IncidentExtraction(**parsed)
