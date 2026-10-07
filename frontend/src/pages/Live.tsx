import { useCallback, useEffect, useRef, useState } from "react"; import { useNavigate, useParams } from "react-router-dom";
import { ArrowRight, Mic, Send, SkipForward, Square, Volume2 } from "lucide-react";
import { getHealth, getTTS, startInterview, submitAnswer, uploadAudio } from "../services/api"; import { useAudioRecorder, type Recording } from "../hooks/useAudioRecorder";
import { Bar, Card, ErrorBox, Loading, btnGhost, btnPrimary } from "../components/ui"; import { personaByKey } from "../lib/personas";
import type { AnswerResult, Health, Question } from "../types/interview";
type Phase = "idle" | "transcribing" | "analyzing" | "next";
const fmt = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
export default function Live() {
  const id = Number(useParams().id); const nav = useNavigate(); const rec = useAudioRecorder();
  const [q, setQ] = useState<Question | null>(null); const [total, setTotal] = useState(0); const [phase, setPhase] = useState<Phase>("idle");
  const [text, setText] = useState(""); const [err, setErr] = useState(""); const [speaking, setSpeaking] = useState(false);
  const [info, setInfo] = useState(""); const [pending, setPending] = useState<Question | null>(null); const [elapsed, setElapsed] = useState(0);
  const health = useRef<Health | null>(null); const audio = useRef<HTMLAudioElement | null>(null); const recog = useRef<any>(null); const clip = useRef<Recording | null>(null); const base = useRef("");

  const speak = useCallback(async (t: string) => {
    window.speechSynthesis?.cancel(); audio.current?.pause(); setSpeaking(true);
    try {
      if (health.current?.tts === "elevenlabs") { const a = new Audio(URL.createObjectURL(await getTTS(t))); audio.current = a; a.onended = () => setSpeaking(false); await a.play(); return; }
    } catch { /* fall back to browser voice */ }
    if (window.speechSynthesis) { const u = new SpeechSynthesisUtterance(t); u.onend = () => setSpeaking(false); u.onerror = () => setSpeaking(false); window.speechSynthesis.speak(u); } else setSpeaking(false);
  }, []);
  const show = useCallback((n: Question) => { setQ(n); setText(""); clip.current = null; setInfo(""); setPhase("idle"); setPending(null); speak(n.text); }, [speak]);
  useEffect(() => {
    let live = true; getHealth().then((h) => (health.current = h)).catch(() => {});
    startInterview(id).then((r) => { if (live) { setTotal(r.total); show(r.question); } }).catch((e) => setErr(e.message));
    const t = window.setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => { live = false; window.clearInterval(t); window.speechSynthesis?.cancel(); audio.current?.pause(); recog.current?.stop(); };
  }, [id, show]);

  async function startRec() {
    window.speechSynthesis?.cancel(); audio.current?.pause(); setSpeaking(false); setErr("");
    if (!(await rec.start())) return;
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SR) { base.current = text; const r = new SR(); r.continuous = true; r.interimResults = true;
      r.onresult = (e: any) => { let s = ""; for (const x of e.results) s += x[0].transcript; setText((base.current + " " + s).trim()); }; r.onerror = () => {}; r.start(); recog.current = r; }
  }
  async function stopRec() { recog.current?.stop(); clip.current = await rec.stop(); }
  async function submit(skipped = false) {
    setErr("");
    if (rec.recording) { recog.current?.stop(); clip.current = await rec.stop(); }
    const c = clip.current; const t = text.trim();
    if (!skipped && !c && !t) { setErr("Please record or type an answer first."); return; }
    try {
      let r: AnswerResult; const words = t.split(/\s+/).filter(Boolean).length;
      if (skipped) { setPhase("analyzing"); r = await submitAnswer(id, { transcript: "", duration: 0, skipped: true }); }
      else if (c) {
        setPhase("transcribing");
        try { r = await uploadAudio(id, c.blob, c.seconds); if (r.transcript) setText(r.transcript); setPhase("analyzing"); }
        catch (e) { const m = (e as Error).message; if (t && /whisper|audio|recording/i.test(m)) { setPhase("analyzing"); r = await submitAnswer(id, { transcript: t, duration: c.seconds }); } else throw e; }
      } else { setPhase("analyzing"); r = await submitAnswer(id, { transcript: t, duration: Math.max(10, Math.round(words / 2.5)) }); }
      if (r.analysis) setInfo(`Answer received · transcript generated · analysis complete — ${r.analysis.words} words, ${r.analysis.fillers.count} filler words`);
      if (r.done) { nav(`/report/${id}`); return; }
      setPhase("next"); await new Promise((res) => setTimeout(res, 900));
      if (r.next && q && r.next.persona !== q.persona) { setPending(r.next); setPhase("idle"); } else if (r.next) show(r.next);
    } catch (e) { setErr((e as Error).message); setPhase("idle"); }
  }
  if (err && !q) return <div className="mx-auto max-w-xl"><ErrorBox msg={err} /></div>;
  if (!q) return <Loading text="AI is thinking..." />;
  if (pending) { const from = personaByKey(q.persona), to = personaByKey(pending.persona); return (
    <Card className="mx-auto max-w-xl py-10 text-center"><div className="text-sm text-stone-500">{from.label} has finished this part</div>
      <div className="my-4 text-sm uppercase tracking-wide text-stone-500">Next interviewer</div>
      <div className={`mx-auto grid h-20 w-20 place-items-center rounded-full text-white ${to.solid}`}><to.Icon className="h-9 w-9" /></div>
      <h2 className="mt-3 text-2xl font-semibold">{to.label}</h2><p className="mt-1 text-stone-600">Get ready for a different style of interview.</p>
      <button className={`${btnPrimary} mt-6`} onClick={() => show(pending)}>Continue <ArrowRight className="h-4 w-4" /></button></Card>); }
  const p = personaByKey(q.persona); const busy = phase !== "idle";
  const status = phase === "transcribing" ? "Transcribing your answer..." : phase === "analyzing" ? "Analyzing your response..." : phase === "next" ? "Generating follow-up question..." : rec.recording ? "Listening..." : speaking ? "Speaking..." : "Your turn";
  return (<div className="space-y-4">
    <div><div className="mb-1 flex justify-between text-sm text-stone-600"><span>Question {q.number} / {total}</span><span>Elapsed {fmt(elapsed)}</span></div><Bar value={((q.number - 1) / Math.max(total, 1)) * 100} color={p.hex} /></div>
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className={`${p.soft} ${p.border}`}>
        <div className="flex items-center gap-3"><div className="relative">{speaking && <span className={`ring-pulse absolute inset-0 rounded-full ${p.solid}`} />}
          <div className={`relative grid h-16 w-16 place-items-center rounded-full text-white ${p.solid}`}><p.Icon className="h-7 w-7" /></div></div>
          <div><div className="text-lg font-semibold">{q.persona_label}</div><div className={`text-sm ${p.text}`}>🟢 AI Interviewer · {p.tagline}</div></div></div>
        {q.follow_up && <span className={`mt-4 inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold text-white ${p.solid}`}>Follow-up</span>}
        <blockquote className="mt-3 text-xl leading-snug">“{q.text}”</blockquote>
        <div className="mt-5 flex items-center gap-3"><button className={btnGhost} onClick={() => speak(q.text)} disabled={busy}><Volume2 className="h-4 w-4" />Replay Question</button>
          <span className="text-sm text-stone-600" aria-live="polite">{status}</span></div></Card>
      <Card><div className="flex items-center justify-between"><h2 className="font-semibold">Your Answer</h2><span className="tabular-nums text-sm text-stone-600">{rec.recording ? `● ${fmt(rec.seconds)}` : "00:00"}</span></div>
        <textarea className="mt-3 h-40 w-full rounded-xl border border-stone-300 p-3 text-sm focus-visible:outline-2 focus-visible:outline-blue-600" value={text} disabled={busy} onChange={(e) => setText(e.target.value)} placeholder="Your speech will appear here... (you can also type)" />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {!rec.recording ? <button className={btnPrimary} disabled={busy} onClick={startRec}><Mic className="h-4 w-4" />Start Recording</button>
            : <button className={`${btn2} bg-red-600`} onClick={stopRec}><span className="relative flex h-3 w-3"><span className="ring-pulse absolute inset-0 rounded-full bg-white" /><Square className="relative h-3 w-3" /></span>Stop Recording</button>}
          <button className={btnPrimary} disabled={busy} onClick={() => submit(false)}><Send className="h-4 w-4" />Submit Answer</button>
          <button className={btnGhost} disabled={busy} onClick={() => submit(true)}><SkipForward className="h-4 w-4" />Skip</button></div>
        {busy && <div className="mt-3"><Loading text={status} /></div>}
        {info && !busy && <p className="mt-3 text-sm text-emerald-700">{info}</p>}
        <div className="mt-3"><ErrorBox msg={err || rec.error} /></div></Card></div></div>);
}
const btn2 = "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium text-white hover:opacity-90";
