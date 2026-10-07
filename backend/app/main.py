import io, os
from datetime import datetime
from statistics import mean
from typing import Literal
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .config import settings
from .db import Session, Interview, Question, Answer
from . import llm, speech, questions
from .personas import PERSONAS

app = FastAPI(title="AI Mock Interview Panel")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors, allow_methods=["*"], allow_headers=["*"])

# State machine: START -> QUESTION -> ANALYZING -> QUESTION ... -> COMPLETE
TRANSITIONS = {"START": {"QUESTION"}, "QUESTION": {"ANALYZING"}, "ANALYZING": {"QUESTION", "COMPLETE"}, "COMPLETE": set()}

def set_state(iv, new):
    if new not in TRANSITIONS[iv.state]:
        raise HTTPException(409, f"Invalid action: interview is in state {iv.state}.")
    iv.state = new

class InterviewIn(BaseModel):
    candidate: str = Field(min_length=1, max_length=120)
    role: str = "Software Engineer"; level: str = "Fresher"; itype: str = "Mixed"
    mode: Literal["technical_hr", "strict_manager", "friendly_hr", "panel"] = "panel"
    difficulty: Literal["Easy", "Medium", "Hard"] = "Medium"
    duration: int = Field(10, ge=1, le=60); total: int = Field(5, ge=1, le=20)
    resume: str = Field("", max_length=20000); jd: str = Field("", max_length=8000)

class AnswerIn(BaseModel):
    transcript: str = Field("", max_length=8000)
    duration: float = Field(30, ge=0, le=1800)
    skipped: bool = False

def _get(db, id):
    iv = db.get(Interview, id)
    if not iv: raise HTTPException(404, "Interview not found.")
    return iv

def qd(q):
    return {"id": q.id, "number": q.number, "persona": q.persona, "persona_label": PERSONAS[q.persona]["label"],
            "text": q.text, "type": q.qtype, "category": (q.meta or {}).get("category"), "difficulty": q.difficulty, "follow_up": q.follow_up}

def _add_question(iv, data):
    q = Question(number=len(iv.questions) + 1, persona=data["persona"], text=data["text"], qtype=data["qtype"],
                 difficulty=data["difficulty"], topics=data["topics"], follow_up=data["follow_up"], meta=data["meta"])
    iv.questions.append(q); iv.state = "QUESTION"
    return q

def _score(a): return 0.5 * a.content_score + 0.2 * a.communication_score + 0.15 * a.confidence_score + 0.15 * a.structure_score

@app.get("/api/health")
def health():
    return {"status": "ok", "demo_mode": settings.demo, "model": settings.ollama_model,
            "tts": "elevenlabs" if settings.el_key else "browser"}

@app.post("/api/resume")
async def resume(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"): raise HTTPException(422, "Please upload a PDF file.")
    try:
        from pypdf import PdfReader
        text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(await file.read())).pages)
    except Exception:
        raise HTTPException(422, "Could not read that PDF.")
    return {"text": text[:20000]}

@app.post("/api/interviews")
def create(body: InterviewIn):
    with Session() as db:
        iv = Interview(candidate=body.candidate, role=body.role, level=body.level, itype=body.itype, mode=body.mode,
                       difficulty=body.difficulty, duration=body.duration, total=body.total, resume=body.resume, jd=body.jd)
        db.add(iv); db.commit()
        return {"id": iv.id, "state": iv.state}

@app.get("/api/interviews")
def history():
    with Session() as db:
        out = []
        for iv in db.query(Interview).order_by(Interview.id.desc()).all():
            ans = [q.answer for q in iv.questions if q.answer]
            out.append({"id": iv.id, "date": iv.start_time.isoformat(), "role": iv.role, "type": iv.itype, "mode": iv.mode,
                        "status": iv.state, "overall": iv.overall_score,
                        "content": round(mean(a.content_score for a in ans)) if ans else None,
                        "communication": round(mean(a.communication_score for a in ans)) if ans else None,
                        "confidence": round(mean(a.confidence_score for a in ans)) if ans else None})
        return out

@app.get("/api/interviews/{id}")
def get_one(id: int):
    with Session() as db:
        iv = _get(db, id)
        return {"id": iv.id, "state": iv.state, "candidate": iv.candidate, "total": iv.total, "duration": iv.duration,
                "questions": [qd(q) for q in iv.questions]}

@app.delete("/api/interviews/{id}")
def delete(id: int):
    with Session() as db:
        db.delete(_get(db, id)); db.commit()
        return {"deleted": id}

@app.post("/api/interviews/{id}/start")
async def start(id: int):
    with Session() as db:
        iv = _get(db, id)
        if iv.questions: return {"question": qd(iv.questions[-1]), "total": iv.total}
        q = _add_question(iv, await questions.generate(iv, 1, None))
        db.commit()
        return {"question": qd(q), "total": iv.total}

async def _advance(db, iv, analysis):
    """After an answer is stored: complete, or generate the next question."""
    if len(iv.questions) >= iv.total:
        set_state(iv, "COMPLETE"); iv.end_time = datetime.utcnow()
        iv.overall_score = round(mean(_score(q.answer) for q in iv.questions if q.answer), 1)
        db.commit()
        return {"done": True, "analysis": analysis}
    q = _add_question(iv, await questions.generate(iv, len(iv.questions) + 1, analysis))
    db.commit()
    return {"done": False, "analysis": analysis, "next": qd(q)}

async def _process(id, tr, dur, skipped):
    with Session() as db:
        iv = _get(db, id)
        if iv.state != "QUESTION": raise HTTPException(409, "There is no open question to answer.")
        q = iv.questions[-1]
        if skipped:
            a = {"content": 0, "communication": 0, "confidence": 0, "structure": {"score": 0, "detected": [], "missing": []},
                 "fillers": {"count": 0, "per_min": 0, "most_used": None}, "tone": {"label": "neutral", "certainty": 0},
                 "wpm": 0, "words": 0, "strengths": [], "missing": ["Question skipped"], "feedback": "Skipped.",
                 "better_answer": "", "filler_tip": ""}
            tr = "(skipped)"
        else:
            if len(tr.split()) < 2: raise HTTPException(422, "Empty answer. Please speak or type your answer.")
            a = await llm.analyze_answer(iv, q, tr, dur)
        set_state(iv, "ANALYZING")
        q.answer = Answer(transcript=tr, duration=dur, content_score=a["content"], communication_score=a["communication"],
                          confidence_score=a["confidence"], structure_score=a["structure"]["score"],
                          filler_count=a["fillers"]["count"], tone=a["tone"]["label"], analysis=a)
        db.commit()
        try:
            return await _advance(db, iv, a)
        except HTTPException:
            raise

@app.post("/api/interviews/{id}/answer")
async def answer(id: int, body: AnswerIn):
    return await _process(id, body.transcript.strip(), body.duration, body.skipped)

@app.post("/api/interviews/{id}/audio")
async def audio(id: int, file: UploadFile = File(...), duration: float = Form(30)):
    data = await file.read()
    if len(data) < 500: raise HTTPException(422, "Recording was empty. Please try again.")
    res = await run_in_threadpool(speech.transcribe_file, data)
    out = await _process(id, res["transcript"], res["duration"] or duration, False)
    return {**out, "transcript": res["transcript"]}

@app.post("/api/interviews/{id}/next-question")
async def next_q(id: int):
    """Retry endpoint if question generation failed after an answer was saved."""
    with Session() as db:
        iv = _get(db, id)
        if iv.state != "ANALYZING": raise HTTPException(409, "Nothing to generate right now.")
        return await _advance(db, iv, iv.questions[-1].answer.analysis)

@app.post("/api/interviews/{id}/complete")
def complete(id: int):
    with Session() as db:
        iv = _get(db, id)
        done = [q for q in iv.questions if q.answer]
        if not done: raise HTTPException(422, "Answer at least one question before finishing.")
        iv.state = "COMPLETE"; iv.end_time = datetime.utcnow()
        iv.overall_score = round(mean(_score(q.answer) for q in done), 1); db.commit()
        return {"overall": iv.overall_score}

@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    return await run_in_threadpool(speech.transcribe_file, await file.read())

class TTSIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)

@app.post("/api/tts")
async def tts(body: TTSIn):
    return Response(await speech.tts(body.text), media_type="audio/mpeg")

@app.get("/api/interviews/{id}/report")
async def report(id: int):
    with Session() as db:
        iv = _get(db, id)
        done = [q for q in iv.questions if q.answer]
        if not done: raise HTTPException(422, "No answered questions yet.")
        A = [q.answer for q in done]
        per_q = [{"n": q.number, "persona": PERSONAS[q.persona]["label"], "q": q.text, "answer": q.answer.transcript,
                  "score": round(_score(q.answer)), "content": q.answer.content_score,
                  "communication": q.answer.communication_score, "confidence": q.answer.confidence_score,
                  "fillers": q.answer.filler_count, "tone": q.answer.tone,
                  "good": q.answer.analysis.get("strengths", []), "missing": q.answer.analysis.get("missing", []),
                  "better": q.answer.analysis.get("better_answer", ""),
                  "fillers_detail": q.answer.analysis.get("fillers", {}).get("breakdown", {}),
                  "structure": q.answer.analysis.get("structure", {}), "duration": q.answer.duration} for q in done]
        secs = sum(a.duration for a in A); fc = sum(a.filler_count for a in A)
        from collections import Counter
        bd = Counter()
        for a in A: bd.update(a.analysis.get("fillers", {}).get("breakdown", {}))
        fb = await llm.final_feedback(iv, per_q)
        return {"candidate": iv.candidate, "role": iv.role, "type": iv.itype, "date": iv.start_time.isoformat(),
                "overall": iv.overall_score or round(mean(p["score"] for p in per_q), 1),
                "categories": {"Technical / content": round(mean(a.content_score for a in A)),
                               "Communication": round(mean(a.communication_score for a in A)),
                               "Estimated confidence": round(mean(a.confidence_score for a in A)),
                               "Answer structure": round(mean(a.structure_score for a in A))},
                "fillers": {"total": fc, "per_min": round(fc / max(secs, 1) * 60, 1),
                            "most_used": bd.most_common(1)[0][0] if bd else None},
                "avg_wpm": round(mean(a.analysis.get("wpm", 0) for a in A)), "avg_answer_sec": round(secs / len(A)),
                "filler_breakdown": dict(bd),
                "questions": per_q, "feedback": fb,
                "disclaimer": "Scores are AI/heuristic estimates. Confidence is an interview-communication estimate, not a psychological measurement."}

@app.get("/api/dev/persona-diversity")
def persona_diversity(role: str = "Software Engineer", n: int = 10):
    return questions.simulate(role, max(3, min(n, 15)))

_static = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=_static, html=True), name="static")
