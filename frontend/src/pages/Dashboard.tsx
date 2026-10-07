import { useEffect, useState } from "react"; import { Link } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getInterviewHistory } from "../services/api"; import { Card, ErrorBox, Loading, Stat, btnPrimary } from "../components/ui"; import type { HistoryItem } from "../types/interview";
export default function Dashboard() {
  const [h, setH] = useState<HistoryItem[] | null>(null); const [err, setErr] = useState("");
  useEffect(() => { getInterviewHistory().then(setH).catch((e) => setErr(e.message)); }, []);
  if (err) return <ErrorBox msg={err} />; if (!h) return <Loading text="Loading your dashboard..." />;
  const done = h.filter((i) => i.overall != null); const avg = done.length ? Math.round(done.reduce((s, i) => s + (i.overall ?? 0), 0) / done.length) : 0;
  const trend = [...done].reverse().map((i, n) => ({ name: `#${i.id}`, n, Overall: Math.round(i.overall ?? 0), Technical: i.content, Communication: i.communication }));
  return (<div className="space-y-6"><div className="flex items-center justify-between"><h1 className="text-3xl font-semibold">Ready for your next interview?</h1><Link to="/setup" className={btnPrimary}>Start New Interview</Link></div>
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4"><Stat label="Total interviews" value={h.length} /><Stat label="Average score" value={done.length ? avg : "—"} />
      <Stat label="Latest score" value={done[0] ? Math.round(done[0].overall ?? 0) : "—"} sub={done[0]?.role} /><Stat label="Latest communication" value={done[0]?.communication ?? "—"} /></div>
    <Card><h2 className="mb-2 font-semibold">Improvement trend</h2>{trend.length > 1 ? <div className="h-64"><ResponsiveContainer><LineChart data={trend}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis domain={[0, 100]} /><Tooltip /><Legend />
      <Line dataKey="Overall" stroke="#1c1917" strokeWidth={2} /><Line dataKey="Technical" stroke="#2563eb" /><Line dataKey="Communication" stroke="#059669" /></LineChart></ResponsiveContainer></div> : <p className="text-sm text-stone-600">Complete two interviews to see your trend.</p>}</Card>
    <Card><h2 className="mb-2 font-semibold">Recent interviews</h2>{h.slice(0, 5).map((i) => <Link key={i.id} to={`/report/${i.id}`} className="flex justify-between border-t border-stone-100 py-2 text-sm hover:bg-stone-50"><span>#{i.id} · {i.role}</span><span>{i.overall != null ? Math.round(i.overall) : i.status}</span></Link>)}{!h.length && <p className="text-sm text-stone-600">No interviews yet.</p>}</Card></div>);
}
