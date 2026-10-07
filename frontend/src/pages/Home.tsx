import { Link } from "react-router-dom"; import { ArrowRight } from "lucide-react";
import { PERSONAS } from "../lib/personas"; import { Card, btnPrimary } from "../components/ui";
export default function Home() {
  return (<div className="space-y-10">
    <section className="py-8 text-center"><h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">AI Mock Interview Panel</h1>
      <p className="mx-auto mt-3 max-w-xl text-lg text-stone-600">Practice real interviews with three different AI interviewers.</p>
      <Link to="/setup" className={`${btnPrimary} mt-6 !px-6 !py-3 text-base`}>Start Mock Interview <ArrowRight className="h-4 w-4" /></Link></section>
    <section className="grid gap-4 md:grid-cols-3">{Object.entries(PERSONAS).map(([k, p]) => (
      <Card key={k} className={`${p.soft} ${p.border}`}><div className={`mb-3 grid h-11 w-11 place-items-center rounded-xl text-white ${p.solid}`}><p.Icon className="h-5 w-5" /></div>
        <h2 className="text-lg font-semibold">{p.label}</h2><p className={`text-sm ${p.text}`}>{p.tagline}</p>
        <ul className="mt-3 space-y-1 text-sm text-stone-700">{p.topics.map((t) => <li key={t}>• {t}</li>)}</ul></Card>))}</section>
  </div>);
}
