"""Persona-specific question engine: separate banks, role/resume awareness, adaptive follow-ups,
difficulty adaptation and anti-repetition (lexical similarity; no embedding model needed)."""
import json, math, os, random, re
from collections import Counter
from types import SimpleNamespace as NS
from .config import settings
from .personas import PERSONAS, PANEL, FOLLOW_UPS, RESUME_Q, persona_for
from . import llm

_dir = os.path.join(os.path.dirname(__file__), "question_bank")
BANK = {p: [dict(cat=c, text=t, diff=d, roles=set(r.split(","))) for c, t, d, r in
            json.load(open(os.path.join(_dir, f + ".json")))]
        for p, f in (("technical_hr", "technical"), ("strict_manager", "manager"), ("friendly_hr", "friendly_hr"))}
CATS = {p: {e["cat"] for e in v} | {"resume"} for p, v in BANK.items()}
GROUP = {"AI/ML Engineer": "ml", "Data Analyst": "data", "Product Manager": "pm"}
DR = {"easy": 0, "medium": 1, "hard": 2}
_STOP = set("a an the of to and or in on for is are do you your how what would we with that this it as at be by can did have has".split())
TECH = re.compile(r"\b(mongodb|mysql|postgres(?:ql)?|redis|random forest|logistic regression|react|spring boot|django|flask|fastapi|"
                  r"node(?:\.js)?|docker|kubernetes|tensorflow|pytorch|sql|kafka|aws|graphql|cnn|lstm)\b", re.I)

def _t(s): return [w[:5] for w in re.findall(r"[a-z]+", s.lower()) if w not in _STOP and len(w) > 2]

def sim(a, b):
    """Cosine similarity of stemmed content words (0..1)."""
    A, B = Counter(_t(a)), Counter(_t(b))
    n = math.sqrt(sum(v * v for v in A.values()) * sum(v * v for v in B.values()))
    return sum(A[k] * B[k] for k in A) / n if n else 0.0

def _max_sim(t, used): return max([sim(t, u) for u in used] or [0.0])
def _score(a): return 0.5 * a["content"] + 0.2 * a["communication"] + 0.15 * a["confidence"] + 0.15 * a["structure"]["score"]
def _meta(q): return q.meta or {}

def mk(persona, cat, text, diff, follow=False, depth=0):
    return {"persona": persona, "category": cat, "question": text, "difficulty": diff, "question_type": PERSONAS[persona]["qtype"],
            "purpose": f"evaluate {cat.replace('_', ' ')}", "expected_topics": PERSONAS[persona]["topics"],
            "follow_up_possible": True, "is_repeat": False, "is_follow_up": follow, "depth": depth}

def resume_project(text):
    m = re.search(r"(?:developed|built|created|designed|implemented)\s+(?:an?\s+|the\s+)?(.{8,70}?)(?:\s+(?:using|with|for|that)\b|[.,;\n]|$)", text or "", re.I)
    return m.group(1).strip() if m else None

def target_difficulty(iv, last):
    if not last: return iv.difficulty.lower()
    s = _score(last)
    return "hard" if s > 80 else "medium" if s >= 50 else "easy"

def _depth(iv):
    d = 0
    for q in reversed(iv.questions):
        if not q.follow_up: break
        d += 1
    return d

def follow_up(iv, persona, last):
    """Persona-specific probing of the previous answer (only inside the same persona's thread)."""
    if not last or not iv.questions or last.get("words", 1) == 0: return None
    prev = iv.questions[-1]
    if prev.persona != persona: return None
    d, s, miss = _depth(iv), _score(last), last["structure"]["missing"]
    ans = prev.answer.transcript if prev.answer else ""
    fu = FOLLOW_UPS[persona]
    if persona == "strict_manager" and d < 3 and s < 78: t = fu[d]
    elif persona == "technical_hr" and d < 2 and s < 80:
        m = TECH.search(ans)
        t = (f"You mentioned {m.group(0)}. What specific characteristics of your problem made it the right choice over the alternatives?"
             if m and d == 0 else fu[d])
    elif persona == "friendly_hr" and d < 2 and s < 80 and ("Action" in miss or "Result" in miss):
        t = fu[0 if "Action" in miss else 1]
    else: return None
    if _max_sim(t, [q.text for q in iv.questions]) >= settings.sim: return None   # never reuse a probe verbatim
    return mk(persona, _meta(prev).get("category", "follow_up"), t, "easy" if s < 50 else prev.difficulty, True, d + 1)

def bank_pick(iv, persona, diff, rng):
    qs = iv.questions; used = [q.text for q in qs]
    mine = [q for q in qs if q.persona == persona and not q.follow_up]
    own = {_meta(q).get("category") for q in mine}
    other = {_meta(q).get("category") for q in qs if q.persona != persona}
    if persona == "friendly_hr" and not mine:
        e = next((e for e in BANK[persona] if e["cat"] == "introduction" and e["text"] not in used), None)
        if e: return mk(persona, e["cat"], e["text"], "easy")
    if iv.resume and "resume" not in own:
        p = resume_project(iv.resume)
        if p: return mk(persona, "resume", RESUME_Q[persona].format(p=p), "medium")
    g = GROUP.get(iv.role, "swe")
    def ok(e, relax):
        return ((relax or "*" in e["roles"] or g in e["roles"]) and e["cat"] not in other
                and _max_sim(e["text"], used) < settings.sim)
    for relax in (False, True):
        pool = [e for e in BANK[persona] if ok(e, relax)]
        if pool: break
    if not pool: pool = sorted(BANK[persona], key=lambda e: _max_sim(e["text"], used))[:1]
    fresh = [e for e in pool if e["cat"] not in own] or pool
    best = min(abs(DR[e["diff"]] - DR[diff]) for e in fresh)
    e = rng.choice([e for e in fresh if abs(DR[e["diff"]] - DR[diff]) == best])
    return mk(persona, e["cat"], e["text"], e["diff"])

async def generate(iv, number, last):
    """Pick the persona, decide follow-up vs fresh question, let the LLM adapt it, validate against history."""
    persona = persona_for(iv.mode, number); P = PERSONAS[persona]
    diff = target_difficulty(iv, last)
    seed = follow_up(iv, persona, last) or bank_pick(iv, persona, diff, random.Random((iv.id or 0) * 1000 + number))
    used = [q.text for q in iv.questions]
    other = {_meta(q).get("category") for q in iv.questions if q.persona != persona}
    last_ans = iv.questions[-1].answer.transcript if iv.questions and iv.questions[-1].answer else "none"
    data = await llm.chat_json(
        f"{P['system']}\nEvaluation criteria: {P['criteria']}\nFollow-up strategy: {P['follow_up']}\nDifficulty strategy: {P['difficulty']}",
        f"Candidate: {iv.candidate}; role: {iv.role}; level: {iv.level}; question {number}/{iv.total}; target difficulty: {diff}\n"
        f"Resume: {llm._cut(iv.resume, 1200)}\nJob description: {llm._cut(iv.jd, 600)}\n"
        f"Already asked in this interview, by ALL interviewers (never repeat or reword; test a different skill): {json.dumps([u[:90] for u in used[-10:]])}\n"
        f"Candidate's last answer: {llm._cut(last_ans, 500)}\nYour allowed categories: {sorted(CATS[persona])}\n"
        f"Suggested {'follow-up' if seed['is_follow_up'] else 'question'} (category {seed['category']}, purpose {seed['purpose']}): {seed['question']}\n"
        "Adapt it to the candidate's resume / last answer, keep the category and purpose, speak in your persona's voice. One question only.\n"
        'JSON: {"category":"...","question":"...","difficulty":"easy|medium|hard","question_type":"...","purpose":"...","expected_topics":["..."],"follow_up_possible":true}')
    if data is None and not settings.demo: raise llm._unavailable()
    d = seed
    t = str((data or {}).get("question", "")).strip()
    cat = (data or {}).get("category")
    if t and _max_sim(t, used) < settings.sim and cat not in other:      # validation: else keep the bank/seed question
        d = {**seed, "question": t, "category": cat if cat in CATS[persona] else seed["category"],
             "expected_topics": data.get("expected_topics") or seed["expected_topics"]}
    return {"persona": persona, "text": d["question"], "qtype": d["question_type"], "difficulty": d["difficulty"],
            "topics": d["expected_topics"], "follow_up": d["is_follow_up"],
            "meta": {"category": d["category"], "purpose": d["purpose"], "depth": d["depth"],
                     "max_similarity": round(_max_sim(d["question"], used), 2)}}

def simulate(role, n=10):
    """Developer test: n questions per persona generated into one shared history (bank only, deterministic)."""
    iv = NS(id=1, role=role, resume="", difficulty="Medium", questions=[])
    cols = {p: [] for p in PERSONAS}
    for i in range(n * 6):
        p = PANEL[i % 3]
        if len(cols[p]) >= n: continue
        d = bank_pick(iv, p, ["easy", "medium", "hard"][i % 3 if i % 3 else 1], random.Random(i))
        iv.questions.append(NS(text=d["question"], persona=p, follow_up=False, meta={"category": d["category"]}, answer=None))
        cols[p].append({"question": d["question"], "category": d["category"], "purpose": d["purpose"], "difficulty": d["difficulty"]})
    allq = [(p, x) for p in cols for x in cols[p]]
    dup = sum(1 for i in range(len(allq)) for j in range(i) if sim(allq[i][1]["question"], allq[j][1]["question"]) >= settings.sim)
    close = sum(1 for i in range(len(allq)) for j in range(i) if 0.5 <= sim(allq[i][1]["question"], allq[j][1]["question"]) < settings.sim)
    def overlap(key):
        seen = {}
        for p, x in allq: seen.setdefault(x[key], set()).add(p)
        return sum(1 for v in seen.values() if len(v) > 1)
    bad = sum(1 for p, x in allq if x["category"] not in CATS[p] or
              (p == "technical_hr" and re.search(r"about yourself|strengths|see yourself", x["question"], re.I)))
    cat_o, int_o = overlap("category"), overlap("purpose")
    score = max(0, 100 - 25 * dup - 4 * close - 6 * cat_o - 6 * int_o - 20 * bad)
    return {"role": role, "columns": cols, "metrics": {"diversity_score": score, "duplicates": dup, "similar_pairs": close,
            "category_overlap": cat_o, "intent_overlap": int_o, "persona_mismatch": bad,
            "similarity_method": "lexical cosine (stemmed words), threshold %.2f" % settings.sim}}
