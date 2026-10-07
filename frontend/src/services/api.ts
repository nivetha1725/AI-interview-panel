import type { AnswerResult, Config, Health, HistoryItem, Question, Report } from "../types/interview";
const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export class ApiError extends Error {}
async function raw(path: string, init?: RequestInit, timeoutMs = 120000): Promise<Response> {
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(`${BASE}/api${path}`, { ...init, signal: ctl.signal });
    if (!r.ok) {
      let m = "Something went wrong. Please try again.";
      try { const d = await r.json(); if (typeof d.detail === "string") m = d.detail; else if (Array.isArray(d.detail)) m = "Please check the form fields and try again."; } catch { /* keep default */ }
      throw new ApiError(m);
    }
    return r;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (e instanceof DOMException && e.name === "AbortError") throw new ApiError("The server took too long to respond. Please try again.");
    throw new ApiError("Unable to connect to the interview server. Make sure the backend is running and try again.");
  } finally { clearTimeout(t); }
}
const json = <T,>(path: string, init?: RequestInit) => raw(path, init).then((r) => r.json() as Promise<T>);
const post = (body: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const getHealth = () => json<Health>("/health");
export const uploadResume = (file: File) => { const f = new FormData(); f.append("file", file); return json<{ text: string }>("/resume", { method: "POST", body: f }); };
export const createInterview = (c: Config) => json<{ id: number }>("/interviews", post(c));
export const startInterview = (id: number) => json<{ question: Question; total: number }>(`/interviews/${id}/start`, { method: "POST" });
export const submitAnswer = (id: number, b: { transcript: string; duration: number; skipped?: boolean }) => json<AnswerResult>(`/interviews/${id}/answer`, post(b));
export const uploadAudio = (id: number, blob: Blob, duration: number) => { const f = new FormData(); f.append("file", blob, "answer.webm"); f.append("duration", String(duration)); return json<AnswerResult>(`/interviews/${id}/audio`, { method: "POST", body: f }); };
export const getNextQuestion = (id: number) => json<AnswerResult>(`/interviews/${id}/next-question`, { method: "POST" });
export const getReport = (id: number) => json<Report>(`/interviews/${id}/report`);
export const getInterviewHistory = () => json<HistoryItem[]>("/interviews");
export const deleteInterview = (id: number) => json<{ deleted: number }>(`/interviews/${id}`, { method: "DELETE" });
export const getTTS = (text: string) => raw("/tts", post({ text }), 30000).then((r) => r.blob());
