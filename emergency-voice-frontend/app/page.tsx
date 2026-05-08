"use client";
import IncidentMap from "@/components/IncidentMap";
import { useRef, useState, useCallback } from "react";

export default function Home() {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const IDLE_TIMEOUT_MS = 60_000;

  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [transcript, setTranscript] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [incident, setIncident] = useState<any>(null);
  const [sessionId, setSessionId] = useState<string |null>(null);
  const [sessionEnded, setsessionEnded] = useState(false);
  const [conversation, setConversation] = useState<any[]>([]);

  const clearIdleTimer = () => {
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current);
      idleTimerRef.current = null;
    }
  };

  const resetIdleTimer = useCallback((currentSessionId: string) => {
    clearIdleTimer();
    idleTimerRef.current = setTimeout(async () => {
      await fetch(`http://127.0.0.1:8000/sessions/${currentSessionId}/end/`, { method: "POST" });
      setsessionEnded(true);
      alert("Session ended due to 60 seconds of inactivity.");
    }, IDLE_TIMEOUT_MS);
  }, []);

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

    if (!sessionId){
      alert("Please start a session first")
      return;
    }
    if(sessionEnded){
      alert("This session has ended. Please start a new session")
      return;
    }

    setLoading(true);
    try {
        const formData = new FormData();
        formData.append("file", target, "emergency-audio.wav");

        const response = await fetch(`http://127.0.0.1:8000/sessions/${sessionId}/voice-intake`, {
          method: "POST",
          body: formData,
        });

        const data = await response.json();

        if (!response.ok || data.error){
          throw new Error(data.error || "Failed to process audio")
        }
        
        setTranscript(data.transcript);
        setAiResponse(data.ai_response);
        setIncident(data.incident);

        setConversation((prev) => [
          ...prev,
          {
            transcript: data.transcript,
            ai_response: data.ai_response,
            incident: data.incident,
          },
        ]
        );

        // if (data.audio_b64) {
        //   const bytes = Uint8Array.from(atob(data.audio_b64), c => c.charCodeAt(0));
        //   const blob = new Blob([bytes], { type: "audio/wav" });
        //   setAudioUrl(URL.createObjectURL(blob));
        // }
        if (data.audio_b64) {
         const bytes = Uint8Array.from(atob(data.audio_b64), (c) =>
        c.charCodeAt(0)
      );

        const aiAudioBlob = new Blob([bytes], { type: "audio/wav" });
        const url = URL.createObjectURL(aiAudioBlob);

        setAudioUrl(url);

        const audio = new Audio(url);
        audio.play();
      }
       if (data.resolved) {
      // Optional: show End Session button or message
      console.log("Session resolved");
    }


  } catch (error) {
      console.error("Error sending audio:", error);
      alert("Failed to process audio. Check backend logs.");
  } finally {
      setLoading(false);
      if (sessionId) resetIdleTimer(sessionId);
  }
};

  const startSession = async() => {
    try {
      const response = await fetch ("http://127.0.0.1:8000/sessions/start", {
      method: "POST"
    })
      const data = await response.json();
      console.log("Session respnse", data)
      if(!response.ok) throw new Error (data.detail || "Failed to start session")
      setSessionId(data.session_id);
      setsessionEnded(false);
      setConversation([]);
      setTranscript("");
      setAiResponse("");
      setAudioBlob(null);
      setAudioUrl(null);
      setIncident(null);
      resetIdleTimer(data.session_id);
    } catch(error){
      console.error("failed to start session", error);
      alert("Could not start session. Check backend logs.");
    }
    
  };

  const endSession = async () => {
    if (!sessionId) return;
    clearIdleTimer();
    await fetch(`http://127.0.0.1:8000/sessions/${sessionId}/end/`, { method: "POST" });
    setsessionEnded(true);
  };

  return (
    <main className="min-h-screen bg-black p-8">
      <div className="mx-auto max-w-3xl rounded-xl bg-white p-6 shadow">
        <h1 className="mb-2 text-3xl font-bold">
          VoiceOps AI: Send your Emergency Request
        </h1>

        <p className="mb-6 text-white-600">
          Start the session and record your emergency.
        </p>
        <div className="mb-6 flex w-fit items-center gap-4">
        {!sessionId || sessionEnded ? (
            <button
              onClick={startSession}
              className="rounded bg-green-600 px-3 py-2 text-xs text-white"
            >
              Start New Session
            </button>
          ) : (
            <button
              onClick={endSession}
              className="rounded bg-gray-800 px-4 py-2 text-white"
            >
              End Session
            </button>
          )}
          
          <div className="flex flex-col items-center gap-1">
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={!sessionId || sessionEnded}
              title={isRecording ? "Stop Recording" : "Start Recording"}
              className={`relative flex h-12 w-12 items-center justify-center rounded-full transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${
                isRecording
                  ? "bg-red-600 shadow-[0_0_20px_6px_rgba(239,68,68,0.6)]"
                  : "bg-gray-200 hover:bg-gray-300"
              }`}
            >
              {isRecording && (
                <span className="absolute inset-0 animate-ping rounded-full bg-red-500 opacity-40" />
              )}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill={isRecording ? "white" : "#374151"}
                className="h-7 w-7"
              >
                <path d="M12 1a4 4 0 0 0-4 4v7a4 4 0 0 0 8 0V5a4 4 0 0 0-4-4z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2H3v2a9 9 0 0 0 8 8.94V23h2v-2.06A9 9 0 0 0 21 12v-2h-2z" />
              </svg>
            </button>
            <span className="text-xs text-gray-500">
              {isRecording ? "Recording… click to stop" : "Click to record"}
            </span>
          </div>
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
        {incident?.location_enrichment && (
            <div className="rounded border p-4">
              <h2 className="mb-2 font-bold">Location Enrichment</h2>
              <p><b>Formatted Address:</b> {incident.location_enrichment.formatted_address}</p>
              <p><b>Latitude:</b> {incident.location_enrichment.latitude}</p>
              <p><b>Longitude:</b> {incident.location_enrichment.longitude}</p>
              <p><b>Confidence:</b> {incident.location_enrichment.confidence || "Unknown"}</p>
            </div>
          )}
       </div>
        <div className="mt-6 rounded border p-4">
              <h2 className="mb-3 font-bold">Session Conversation</h2>

              {conversation.length === 0 && (
                <p className="text-gray-500">No conversation yet.</p>
              )}

              {conversation.map((item, index) => (
                <div key={index} className="mb-4 rounded bg-gray-50 p-3">
                  <p>
                    <b>You said:</b> {item.transcript}
                  </p>
                  <p>
                    <b>AI:</b> {item.ai_response}
                  </p>
                </div>
              ))}
        </div>
      <a href="/incidents" className="text-blue-600 underline">
          Go to Dashboard
      </a>
      {incident?.location_enrichment?.latitude &&(
        <IncidentMap
        latitude={incident?.location_enrichment?.latitude}
        longitude={incident?.location_enrichment?.longitude}
        title={incident?.emergency_type || "Emergency Incident"}
        description={
          incident?.location_enrichment?.formatted_address ||
          incident?.location ||
          "Unknown location"
          }
          nearbyResources={incident?.nearby_resources || []}
        />
      )}
      
    </main>
  );
}