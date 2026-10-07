import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { AlertTriangle, Loader2, Mic } from "lucide-react";
import { getHealth } from "../services/api";
import type { Health } from "../types/interview";

export const Card = ({ children, className = "" }: { children: ReactNode; className?: string }) =>
  <div className={`rounded-2xl border border-stone-200 bg-white p-5 shadow-sm ${className}`}>{children}</div>;
export const Loading = ({ text }: { text: string }) =>
  <div role="status" className="flex items-center gap-2 text-stone-600"><Loader2 className="h-4 w-4 animate-spin" />{text}</div>;
export const ErrorBox = ({ msg }: { msg: string }) =>
  msg ? <div role="alert" className="flex gap-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"><AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />{msg}</div> : null;
export const Bar = ({ value, color = "#2563eb" }: { value: number; color?: string }) =>
  <div className="h-2 w-full overflow-hidden rounded-full bg-stone-200"><div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color }} /></div>;
export const Stat = ({ label, value, sub }: { label: string; value: ReactNode; sub?: string }) =>
  <Card><div className="text-sm text-stone-500">{label}</div><div className="mt-1 text-3xl font-semibold tabular-nums">{value}</div>{sub && <div className="text-xs text-stone-500">{sub}</div>}</Card>;
export const btn = "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-50";
export const btnPrimary = `${btn} bg-stone-900 text-white hover:bg-stone-700`;
export const btnGhost = `${btn} border border-stone-300 bg-white hover:bg-stone-100`;

export function Navbar() {
  const [h, setH] = useState<Health | null>(null); const [off, setOff] = useState(false);
  useEffect(() => { getHealth().then(setH).catch(() => setOff(true)); }, []);
  const link = ({ isActive }: { isActive: boolean }) => `rounded-lg px-3 py-1.5 text-sm ${isActive ? "bg-stone-900 text-white" : "text-stone-600 hover:bg-stone-100"}`;
  return (
    <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-3">
        <Link to="/" className="mr-auto flex items-center gap-2 font-semibold"><span className="grid h-8 w-8 place-items-center rounded-lg bg-stone-900 text-white"><Mic className="h-4 w-4" /></span>AI Mock Interview Panel</Link>
        {h?.demo_mode && <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">DEMO MODE</span>}
        {off && <span className="rounded-full bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-800">Backend offline</span>}
        <NavLink to="/dashboard" className={link}>Dashboard</NavLink><NavLink to="/history" className={link}>History</NavLink>
        <Link to="/setup" className={`${btnPrimary} !py-1.5`}>New interview</Link>
      </div>
    </header>
  );
}
