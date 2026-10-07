"""Heuristic answer analytics: fillers, structure, tone, scores. Deterministic (used in demo + as LLM fallback)."""
import re
from collections import Counter

_FILLER = re.compile(r"\b(you know|i mean|um+|uh+|like|actually|basically|so)\b", re.I)
_HEDGE = re.compile(r"\b(maybe|i think|i guess|probably|not sure|kind of|sort of|perhaps)\b", re.I)
_POS = re.compile(r"\b(excited|love|passionate|enjoy|proud|great|happy)\b", re.I)
_DEF = re.compile(r"\b(not my fault|they didn't|blame|unfair)\b", re.I)

def _norm(f):
    f = f.lower()
    return "um" if f.startswith("um") else "uh" if f.startswith("uh") else f

def filler_stats(text, duration):
    hits = [_norm(m) for m in _FILLER.findall(text)]
    minutes = max(duration, 5) / 60
    top = Counter(hits).most_common(1)
    return {"count": len(hits), "per_min": round(len(hits) / minutes, 1),
            "most_used": top[0][0] if top else None,
            "breakdown": dict(Counter(hits))}

_S = {
    "behavioral": {"Situation": r"\b(when|situation|context|at that time|team|once)\b",
                   "Task": r"\b(task|goal|responsib|needed to|had to|objective|my job)\b",
                   "Action": r"\b(i (built|implemented|created|decided|led|wrote|designed|fixed|worked|talked|organi[sz]ed)|my role|i took)\b",
                   "Result": r"(result|outcome|achiev|improv|reduc|increas|learn|%)"},
    "technical": {"Problem": r"\b(problem|issue|requirement|need|challenge)\b",
                  "Approach": r"\b(approach|algorithm|design|strategy|because|instead of)\b",
                  "Implementation": r"\b(implement|used|built|code|class|function|api|database|model)\b",
                  "Result": r"(result|outcome|complexity|performance|accuracy|improv|reduc|%)"},
    "project": {"Problem": r"\b(problem|goal|aim|purpose)\b",
                "Technology": r"\b(python|java|react|sql|flask|django|spring|node|tensorflow|esp32|aws|docker|api)\b",
                "Implementation": r"\b(implement|built|developed|designed|created|i wrote)\b",
                "Challenges": r"\b(challenge|difficult|bug|issue|struggle|tradeoff)\b",
                "Result": r"(result|outcome|accuracy|deployed|improv|reduc|users|%)"},
}

def structure(text, qtype):
    key = "technical" if qtype == "technical" else "project" if qtype == "project" else "behavioral"
    found = [k for k, rx in _S[key].items() if re.search(rx, text, re.I)]
    missing = [k for k in _S[key] if k not in found]
    return {"score": round(100 * len(found) / len(_S[key])), "detected": found, "missing": missing, "framework": key}

def tone(text, fillers_per_min):
    hedges = len(_HEDGE.findall(text)); words = len(text.split())
    if _DEF.search(text): t = "defensive"
    elif hedges >= 3 or words < 15: t = "uncertain"
    elif fillers_per_min > 6: t = "nervous"
    elif _POS.search(text): t = "enthusiastic"
    elif words > 60 and hedges == 0: t = "confident"
    else: t = "neutral"
    certainty = max(20, min(95, 85 - hedges * 10 - int(fillers_per_min * 2) + min(words, 100) // 10))
    return {"label": t, "certainty": certainty}

def heuristic_content(text, topics):
    w = len(text.split()); low = text.lower()
    cov = sum(t.lower() in low for t in topics) / max(len(topics), 1)
    spec = min(1, len(re.findall(r"\b\d+\b|\b(python|java|react|sql|api|docker|flask|django|spring)\b", text, re.I)) / 4)
    return round(min(100, min(1, w / 80) * 45 + cov * 35 + spec * 20))

def analyze(text, duration, qtype, topics):
    """Return all metrics for one answer."""
    words = len(text.split()); f = filler_stats(text, duration)
    st = structure(text, qtype); tn = tone(text, f["per_min"])
    wpm = round(words / max(duration, 5) * 60)
    hedges = len(_HEDGE.findall(text))
    comm = max(10, min(100, 55 + min(words, 120) // 6 - f["per_min"] * 3 + st["score"] // 5))
    conf = max(15, min(95, 80 - f["per_min"] * 3 - hedges * 6 + (8 if 110 <= wpm <= 170 else 0) - (15 if words < 15 else 0)))
    return {"content": heuristic_content(text, topics), "communication": round(comm), "confidence": round(conf),
            "structure": st, "fillers": f, "tone": tn, "wpm": wpm, "words": words}

def suggestions(f):
    if f["count"] == 0: return "No filler words detected. Nice and clean."
    tip = f"Replace \"{f['most_used']}\" with a short pause; silence sounds more confident than filler."
    return tip if f["per_min"] > 3 else "Filler use is low. Keep pausing instead of filling."
