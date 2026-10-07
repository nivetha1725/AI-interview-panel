import { useEffect, useState } from "react"; import { Link, useParams } from "react-router-dom";
import { Bar as RBar, BarChart, CartesianGrid, Legend, PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getReport } from "../services/api"; import { personaByLabel } from "../lib/personas";
import { Bar, Card, ErrorBox, Loading, Stat, btnGhost } from "../components/ui"; import type { Report } from "../types/interview";
const avg = (a: number[]) => (a.length ? Math.round(a.reduce((x, y) => x + y, 0) / a.length) : 0);
const List = ({ t, items }: { t: string; items?: string[] }) => <div><h4 className="text-sm font-semibold">{t}</h4><ul className="mt-1 list-disc pl-5 text-sm text-stone-700">{(items?.length ? items : ["—"]).map((x, i) => <li key={i}>{x}</li>)}</ul></div>;
export default function ReportPage() {
  const id = Number(useParams().id); const [r, setR] = useState<Report | null>(null); const [err, setErr] = useState("");
  useEffect(() => { getReport(id).then(setR).catch((e) => setErr(e.message)); }, [id]);
  if (err) return <ErrorBox msg={err} />; if (!r) return <Loading text="Generating your report..." />;
  const c = r.categories; const groups = [...new Set(r.questions.map((q) => q.persona))];
  const byPersona = groups.map((g) => { const qs = r.questions.filter((q) => q.persona === g); return { name: g, Content: avg(qs.map((q) => q.content)), Communication: avg(qs.map((q) => q.communication)), "Confidence est.": avg(qs.map((q) => q.confidence)) }; });
  const fillers = Object.entries(r.filler_breakdown ?? {}).map(([word, count]) => ({ word, count }));
  const perQ = r.questions.map((q) => ({ name: `Q${q.n}`, score: q.score }));
  return (<div className="space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-2"><div><h1 className="text-3xl font-semibold">Interview Performance Report</h1>
      <p className="text-stone-600">{r.candidate} · {r.role} · {r.type} · {r.date.slice(0, 10)}</p></div>
      <div className="flex gap-2"><button className={btnGhost} onClick={() => window.print()}>Download (print to PDF)</button><Link to="/setup" className={btnGhost}>New interview</Link></div></div>
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="flex flex-col items-center"><h2 className="self-start font-semibold">Overall Performance</h2><div className="relative h-48 w-48">
        <ResponsiveContainer><RadialBarChart innerRadius="75%" outerRadius="100%" data={[{ v: r.overall }]} startAngle={90} endAngle={-270}><PolarAngleAxis type="number" domain={[0, 100]} tick={false} /><RadialBar dataKey="v" cornerRadius={10} fill="#2563eb" background /></RadialBarChart></ResponsiveContainer>
        <div className="absolute inset-0 grid place-items-center text-4xl font-semibold">{Math.round(r.overall)}</div></div></Card>
      <div className="grid grid-cols-2 gap-4 lg:col-span-2">
        <Stat label="Technical / content" value={c["Technical / content"]} /><Stat label="Communication" value={c["Communication"]} />
        <Stat label="Confidence estimate" value={c["Estimated confidence"]} sub="Communication estimate, not psychology" /><Stat label="Answer structure" value={c["Answer structure"]} />
        <Stat label="Avg answer time" value={`${r.avg_answer_sec ?? 0}s`} sub={`${r.avg_wpm} words/min`} /><Stat label="Filler words" value={r.fillers.total} sub={`${r.fillers.per_min}/min`} /></div></div>
    <div className="grid gap-4 lg:grid-cols-2">
      <Card><h2 className="mb-2 font-semibold">Persona-wise performance</h2><div className="h-64"><ResponsiveContainer><BarChart data={byPersona}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis domain={[0, 100]} /><Tooltip /><Legend />
        <RBar dataKey="Content" fill="#2563eb" /><RBar dataKey="Communication" fill="#059669" /><RBar dataKey="Confidence est." fill="#a8a29e" /></BarChart></ResponsiveContainer></div></Card>
      <Card><h2 className="mb-2 font-semibold">Score by question</h2><div className="h-64"><ResponsiveContainer><BarChart data={perQ}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis domain={[0, 100]} /><Tooltip /><RBar dataKey="score" fill="#1c1917" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div></Card></div>
    <Card><h2 className="font-semibold">Filler word analysis</h2><p className="text-sm text-stone-600">Filler Words: {r.fillers.total} · {r.fillers.per_min}/min · most used: {r.fillers.most_used ?? "—"}</p>
      {fillers.length ? <div className="mt-2 h-48"><ResponsiveContainer><BarChart data={fillers}><XAxis dataKey="word" /><YAxis allowDecimals={false} /><Tooltip /><RBar dataKey="count" fill="#f59e0b" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div> : <p className="mt-2 text-sm">No filler words detected.</p>}</Card>
    <Card className="grid gap-4 md:grid-cols-2"><List t="Strengths" items={r.feedback.strengths} /><List t="Areas to improve" items={r.feedback.weaknesses} /><List t="Recommendations" items={r.feedback.recommendations} /><List t="Improvement plan" items={r.feedback.plan} />
      <p className="text-sm md:col-span-2">{r.feedback.overall_feedback}</p></Card>
    <h2 className="text-xl font-semibold">Question-by-question analysis</h2>
    {r.questions.map((q) => { const p = personaByLabel(q.persona); const isTech = p.label === "Technical HR"; return (
      <Card key={q.n} className="space-y-3"><div className="flex flex-wrap items-center gap-2"><span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold text-white ${p.solid}`}>{q.persona}</span><span className="text-sm text-stone-500">Q{q.n}</span><span className="ml-auto text-lg font-semibold">{q.score}/100</span></div>
        <p className="font-medium">{q.q}</p><div className="rounded-xl bg-stone-50 p-3 text-sm"><div className="mb-1 text-xs uppercase text-stone-500">Your answer (transcript)</div>{q.answer}</div>
        {isTech && <div className="grid gap-2 text-sm sm:grid-cols-2"><div>Technical accuracy (content) {q.content}<Bar value={q.content} color={p.hex} /></div><div>Explanation quality (communication) {q.communication}<Bar value={q.communication} color={p.hex} /></div></div>}
        <div className="grid gap-3 md:grid-cols-2"><List t="Strengths" items={q.good} /><List t="Areas to improve" items={q.missing} /></div>
        <div className="text-sm"><b>Filler words ({q.fillers}):</b> {Object.entries(q.fillers_detail ?? {}).map(([w, n]) => `"${w}" → ${n}`).join(", ") || "none"}</div>
        {q.structure?.detected && <div className="flex flex-wrap gap-1 text-xs">{q.structure.detected.map((s) => <span key={s} className="rounded bg-emerald-100 px-2 py-0.5 text-emerald-800">✓ {s}</span>)}{q.structure.missing?.map((s) => <span key={s} className="rounded bg-stone-100 px-2 py-0.5 text-stone-600">✗ {s}</span>)}</div>}
        <div className="text-sm"><b>Suggested better answer:</b> {q.better || "—"}</div></Card>); })}
    <p className="text-xs text-stone-500">{r.disclaimer}</p></div>);
}
