import { useState } from "react"; import { useNavigate } from "react-router-dom"; import { Upload } from "lucide-react";
import { PERSONAS, type PersonaKey } from "../lib/personas"; import { createInterview, uploadResume } from "../services/api";
import { Card, ErrorBox, Loading, btnPrimary } from "../components/ui"; import type { Mode } from "../types/interview";
const ROLES = ["Software Engineer", "Frontend Developer", "Backend Developer", "Full Stack Developer", "AI/ML Engineer", "Data Analyst", "Product Manager"];
const field = "mt-1 w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-blue-600";
export default function Setup() {
  const nav = useNavigate();
  const [f, setF] = useState({ candidate: "", role: ROLES[0], level: "Fresher", difficulty: "Medium", duration: 10, total: 5, jd: "" });
  const [sel, setSel] = useState<PersonaKey[]>(["technical_hr", "strict_manager", "friendly_hr"]);
  const [resume, setResume] = useState(""); const [fname, setFname] = useState(""); const [busy, setBusy] = useState(""); const [err, setErr] = useState("");
  const set = (k: string, v: string | number) => setF((s) => ({ ...s, [k]: v }));
  const toggle = (k: PersonaKey) => setSel((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k]));
  const mode: Mode | null = sel.length === 3 ? "panel" : sel.length === 1 ? sel[0] : null;
  async function pickResume(file?: File) {
    if (!file) return; setErr(""); setBusy("Reading your resume...");
    try { setResume((await uploadResume(file)).text); setFname(file.name); } catch (e) { setErr((e as Error).message); } finally { setBusy(""); }
  }
  async function start() {
    if (!mode) return; setErr(""); setBusy("Creating your interview...");
    try {
      const { id } = await createInterview({ ...f, candidate: f.candidate.trim() || "Candidate", mode, itype: mode === "panel" ? "Panel" : mode === "technical_hr" ? "Technical" : mode === "friendly_hr" ? "HR" : "Behavioral", resume, jd: f.jd });
      nav(`/interview/${id}`);
    } catch (e) { setErr((e as Error).message); setBusy(""); }
  }
  const Sel = ({ k, opts }: { k: keyof typeof f; opts: (string | number)[] }) =>
    <select className={field} value={f[k]} onChange={(e) => set(k, typeof f[k] === "number" ? Number(e.target.value) : e.target.value)}>{opts.map((o) => <option key={o}>{o}</option>)}</select>;
  return (<div className="mx-auto max-w-3xl space-y-5"><h1 className="text-3xl font-semibold">Set up your interview</h1>
    <Card className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm sm:col-span-2">Your name<input className={field} value={f.candidate} onChange={(e) => set("candidate", e.target.value)} placeholder="Candidate name" /></label>
      <label className="text-sm">Target role<Sel k="role" opts={ROLES} /></label><label className="text-sm">Experience level<Sel k="level" opts={["Fresher", "Junior", "Intermediate"]} /></label>
      <label className="text-sm">Difficulty<Sel k="difficulty" opts={["Easy", "Medium", "Hard"]} /></label>
      <label className="text-sm">Duration (minutes)<Sel k="duration" opts={[5, 10, 15, 20]} /></label>
      <label className="text-sm">Number of questions<Sel k="total" opts={[5, 10, 15, 20]} /></label>
      <label className="text-sm">Resume (PDF, optional)<span className="mt-1 flex items-center gap-2 rounded-xl border border-dashed border-stone-300 px-3 py-2 text-stone-600"><Upload className="h-4 w-4" />{fname || "Choose PDF"}
        <input type="file" accept=".pdf" className="sr-only" onChange={(e) => pickResume(e.target.files?.[0])} /></span></label>
      <label className="text-sm sm:col-span-2">Job description (optional, paste text)<textarea rows={3} className={field} value={f.jd} onChange={(e) => set("jd", e.target.value)} /></label>
    </Card>
    <Card><h2 className="font-semibold">Interviewers</h2><div className="mt-3 grid gap-3 sm:grid-cols-3">
      {(Object.keys(PERSONAS) as PersonaKey[]).map((k) => { const p = PERSONAS[k], on = sel.includes(k); return (
        <button key={k} onClick={() => toggle(k)} aria-pressed={on} className={`rounded-xl border-2 p-3 text-left transition ${on ? `${p.soft} ${p.border} border-current ${p.text}` : "border-stone-200 text-stone-500"}`}>
          <p.Icon className="mb-2 h-5 w-5" /><div className="font-medium">{on ? "☑" : "☐"} {p.label}</div><div className="text-xs">{p.tagline}</div></button>); })}</div>
      <p className="mt-3 text-sm text-stone-600">{mode === "panel" ? "All three interviewers will take turns." : mode ? "Single-interviewer mode." : "Select all three interviewers or exactly one. Two-interviewer panels are not supported by the backend yet."}</p></Card>
    <p className="text-xs text-stone-500">Audio may be sent to a speech-to-text service. Transcripts are stored in your local database and can be deleted from History. Scores are estimates; "confidence" measures communication, not psychology.</p>
    <ErrorBox msg={err} />{busy && <Loading text={busy} />}
    <button className={btnPrimary} disabled={!mode || !!busy} onClick={start}>Start Interview</button></div>);
}
