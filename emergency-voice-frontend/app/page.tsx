"use client";

import { useRef, useState } from "react";

export default function Home() {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [transcript, setTranscript] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [incident, setIncident] = useState<any>(null);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorderRef.current = mediaRecorder;
    chunksRef.current = [];

    mediaRecorder.ondataavailable = (event) => {
      chunksRef.current.push(event.data);
    };

    mediaRecorder.onstop = () => {
      const mimeType = mediaRecorder.mimeType || "audio/webm";
      const blob = new Blob(chunksRef.current, { type: mimeType });
      setAudioBlob(blob);
      sendAudio(blob);
    };

    mediaRecorder.start();
    setIsRecording(true);
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const sendAudio = async (blob?: Blob) => {
    const target = blob ?? audioBlob;
    if (!target) return;

    setLoading(true);

    const formData = new FormData();
    formData.append("file", target, "emergency-audio.wav");

    const response = await fetch("http://127.0.0.1:8000/voice-intake", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    setTranscript(data.transcript);
    setAiResponse(data.ai_response);
    setIncident(data.incident);

    if (data.audio_b64) {
      const bytes = Uint8Array.from(atob(data.audio_b64), c => c.charCodeAt(0));
      const blob = new Blob([bytes], { type: "audio/wav" });
      setAudioUrl(URL.createObjectURL(blob));
    }

    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-gray-100 p-8">
      <div className="mx-auto max-w-3xl rounded-xl bg-white p-6 shadow">
        <h1 className="mb-2 text-3xl font-bold">
          VoiceOps AI: Send your Emergency Request
        </h1>

        <p className="mb-6 text-gray-600">
          Record an emergency request and send it to the voice pipeline.
        </p>

        <div className="mb-6 flex gap-4">
          {!isRecording ? (
            <button
              onClick={startRecording}
              className="rounded bg-red-600 px-4 py-2 text-white"
            >
              Start Recording
            </button>
          ) : (
            <button
              onClick={stopRecording}
              className="rounded bg-gray-800 px-4 py-2 text-white"
            >
              Stop Recording
            </button>
          )}
        </div>

        {audioBlob && (
          <div className="mb-6">
            <p className="mb-2 font-semibold">Recorded Audio:</p>
            <audio controls src={URL.createObjectURL(audioBlob)} />
          </div>
        )}

        <div className="mb-4 rounded border p-4">
          <h2 className="mb-2 font-bold">Transcript</h2>
          <p>{transcript || "No transcript yet."}</p>
        </div>

        <div className="rounded border p-4">
          <h2 className="mb-2 font-bold">AI Emergency Response</h2>
          <p>{aiResponse || "No AI response yet."}</p>
        </div>
        {incident && (
          <div className="rounded border p-4">
            <h2 className="mb-2 font-bold">Extracted Incident</h2>
            <p><b>IncidentId:</b> {incident.incident_id}</p>
            <p><b>Status:</b> {incident.status}</p>
            <p><b>Type:</b> {incident.emergency_type}</p>
            <p><b>Severity:</b> {incident.severity}</p>
            <p><b>Location:</b> {incident.location || "Missing"}</p>
            <p><b>Injuries:</b> {String(incident.injuries)}</p>
            <p><b>Symptoms:</b> {incident.symptoms?.join(", ")}</p>
            <p><b>Callback:</b> {incident.callback_number || "Missing"}</p>
            <p><b>Summary:</b> {incident.summary}</p>
            <p><b>Missing Fields:</b> {incident.missing_fields?.join(", ")}</p>
            <p><b>Created At:</b> {incident.created_at}</p>
          </div>
        )}
        {audioUrl && (
          <div className="mt-4 rounded border p-4">
            <h2 className="mb-2 font-bold">AI Audio Response</h2>
            <audio controls autoPlay src={audioUrl} />
          </div>
        )}
      </div>
      <a href="/incidents" className="text-blue-600 underline">
          Go to Dashboard
      </a>
    </main>
  );
}