import { useEffect, useState } from "react"; import { Link } from "react-router-dom"; import { Trash2 } from "lucide-react";
import { deleteInterview, getInterviewHistory } from "../services/api"; import { Card, ErrorBox, Loading } from "../components/ui"; import type { HistoryItem } from "../types/interview";
const label = (m: string) => (m === "panel" ? "3 Personas" : m.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()));
export default function History() {
  const [h, setH] = useState<HistoryItem[] | null>(null); const [err, setErr] = useState("");
  const load = () => getInterviewHistory().then(setH).catch((e) => setErr(e.message)); useEffect(() => { load(); }, []);
  async function del(id: number) { if (confirm("Delete this interview and its transcripts?")) { try { await deleteInterview(id); await load(); } catch (e) { setErr((e as Error).message); } } }
  if (!h) return err ? <ErrorBox msg={err} /> : <Loading text="Loading history..." />;
  return (<div className="space-y-3"><h1 className="text-3xl font-semibold">Interview History</h1><ErrorBox msg={err} />
    {!h.length && <Card>No interviews yet. Start one to see it here.</Card>}
    {h.map((i) => <Card key={i.id} className="flex items-center gap-3"><Link to={`/report/${i.id}`} className="flex-1"><div className="font-medium">Interview #{i.id} · {i.role}</div>
      <div className="text-sm text-stone-600">{label(i.mode)} · {i.date.slice(0, 10)} · {i.status === "COMPLETE" ? "Complete" : "In progress"}</div></Link>
      <div className="text-2xl font-semibold tabular-nums">{i.overall != null ? Math.round(i.overall) : "—"}</div>
      <button aria-label={`Delete interview ${i.id}`} onClick={() => del(i.id)} className="rounded-lg p-2 text-stone-500 hover:bg-stone-100"><Trash2 className="h-4 w-4" /></button></Card>)}</div>);
}
