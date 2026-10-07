"""LLM service (Ollama) with centralized prompts, robust JSON parsing and demo fallbacks."""
import json, re
import httpx
from fastapi import HTTPException
from .config import settings
from .personas import PERSONAS
from . import analyzers

JSON_RULE = "Respond with ONLY one valid JSON object. No prose, no markdown fences."

PROMPTS = {
    "analysis": (
        "Role: {role}. Question ({qtype}): {question}\nExpected topics: {topics}\nCandidate answer: {answer}\n"
        "Evaluate as the {persona} would. Criteria: {criteria}\n"
        'JSON: {{"content_score":0-100,"strengths":["..."],"missing_points":["..."],"follow_up_needed":true,'
        '"feedback":"...","better_answer":"..."}}'),
    "report": (
        "Interview for {role}, candidate {candidate}. Per-question summary (score/100): {summary}\n"
        'JSON: {{"strengths":["..."],"weaknesses":["..."],"recommendations":["..."],"plan":["Day 1: ...","Day 2: ...","Day 3: ..."],'
        '"overall_feedback":"..."}}'),
}

def parse_json(text):
    """Extract -> repair -> give up (returns None)."""
    if not text: return None
    cands = [text] + re.findall(r"\{.*\}", text, re.S)[:1]
    for c in cands:
        for attempt in (c, re.sub(r",\s*([}\]])", r"\1", c), re.sub(r",\s*([}\]])", r"\1", c).replace("'", '"')):
            try:
                d = json.loads(attempt)
                if isinstance(d, dict): return d
            except Exception: pass
    return None

async def chat_json(system, user, timeout=60):
    """Call Ollama; retry once with a stricter prompt. Returns dict or None."""
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                r = await c.post(f"{settings.ollama_url}/api/chat", json={
                    "model": settings.ollama_model, "stream": False, "format": "json",
                    "messages": [{"role": "system", "content": f"{system}\n{JSON_RULE}"},
                                 {"role": "user", "content": user}]})
                r.raise_for_status()
            d = parse_json(r.json()["message"]["content"])
            if d: return d
            user += "\nYour last reply was invalid JSON. Return ONLY the JSON object."
        except Exception:
            return None
    return None

def _unavailable():
    return HTTPException(503, "The AI interviewer (Ollama) is unavailable. Start Ollama, or set DEMO_MODE=true.")

def _cut(s, n): return (s or "none")[:n]

async def analyze_answer(iv, q, transcript, duration):
    """Heuristic metrics + LLM content evaluation (falls back to heuristics)."""
    m = analyzers.analyze(transcript, duration, q.qtype, q.topics or [])
    data = await chat_json("You are a strict, fair interview evaluator.", PROMPTS["analysis"].format(
        role=iv.role, persona=PERSONAS[q.persona]['label'], criteria=PERSONAS[q.persona]['criteria'], qtype=q.qtype, question=q.text, topics=q.topics, answer=_cut(transcript, 1500)))
    if data:
        try: m["content"] = max(0, min(100, int(data.get("content_score", m["content"]))))
        except (TypeError, ValueError): pass
    elif not settings.demo: raise _unavailable()
    d = data or {}
    good = d.get("strengths") or ([f"Covered: {', '.join(m['structure']['detected'])}"] if m["structure"]["detected"] else [])
    miss = d.get("missing_points") or [f"Missing {x}" for x in m["structure"]["missing"]]
    m.update(strengths=good, missing=miss, follow_up_needed=bool(d.get("follow_up_needed", m["content"] < 45)),
             feedback=d.get("feedback") or "Add concrete details, numbers and outcomes.",
             better_answer=d.get("better_answer") or "Use a clear structure and end with a measurable result.",
             filler_tip=analyzers.suggestions(m["fillers"]))
    return m

async def final_feedback(iv, summary):
    data = await chat_json("You are a career coach writing an interview report.",
                           PROMPTS["report"].format(role=iv.role, candidate=iv.candidate, summary=json.dumps(summary)[:3000]))
    if data: return data
    weak = [s["q"][:50] for s in summary if s["score"] < 60]
    return {"strengths": ["Completed the full interview", "Answered every question in a spoken format"],
            "weaknesses": [f"Weak answer: {w}" for w in weak] or ["Add more measurable detail"],
            "recommendations": ["Use STAR for behavioral answers", "Name technologies and trade-offs explicitly", "Pause instead of using filler words"],
            "plan": ["Day 1: Rewrite your weakest answers using STAR.", "Day 2: Revise core topics you missed.", "Day 3: Do a timed mock interview again."],
            "overall_feedback": "Solid attempt. Focus on specificity, structure and results to raise your scores."}
