import { useCallback, useEffect, useRef, useState } from "react";
export interface Recording { blob: Blob; seconds: number }
export function useAudioRecorder() {
  const [recording, setRecording] = useState(false); const [seconds, setSeconds] = useState(0); const [error, setError] = useState("");
  const rec = useRef<MediaRecorder | null>(null); const chunks = useRef<Blob[]>([]); const stream = useRef<MediaStream | null>(null);
  const timer = useRef<number>(0); const secs = useRef(0);
  const release = () => { stream.current?.getTracks().forEach((t) => t.stop()); stream.current = null; window.clearInterval(timer.current); };
  const start = useCallback(async () => {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia) { setError("Your browser does not support microphone recording. Type your answer instead."); return false; }
    try { stream.current = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch { setError("Microphone access was denied. Allow it in your browser's address bar, or type your answer instead."); return false; }
    chunks.current = []; rec.current = new MediaRecorder(stream.current);
    rec.current.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data); };
    rec.current.start(); secs.current = 0; setSeconds(0); setRecording(true);
    timer.current = window.setInterval(() => { secs.current += 1; setSeconds(secs.current); }, 1000);
    return true;
  }, []);
  const stop = useCallback((): Promise<Recording | null> => new Promise((resolve) => {
    const r = rec.current; if (!r || r.state === "inactive") return resolve(null);
    r.onstop = () => { const blob = new Blob(chunks.current, { type: r.mimeType || "audio/webm" }); release(); setRecording(false); resolve({ blob, seconds: Math.max(1, secs.current) }); };
    r.stop();
  }), []);
  useEffect(() => release, []);
  return { recording, seconds, error, start, stop };
}
