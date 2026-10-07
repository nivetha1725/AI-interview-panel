import os, random, tempfile
os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")
os.environ["DEMO_MODE"] = "true"
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:9"
from types import SimpleNamespace as NS
from fastapi.testclient import TestClient
from app.main import app
from app import analyzers, questions
from app.llm import parse_json
from app.personas import persona_for

c = TestClient(app)
STRONG = ("When I led a team project I decided to build the API in Python with Flask and SQL, because it scaled. "
          "My role was to design the database and implement authentication; the result improved speed by 30%. "
          "I learned to compare tradeoffs, and the goal, skills and background of the team mattered.")

def new(mode, **kw):
    iv = c.post("/api/interviews", json={"candidate": "D", "total": 6, "mode": mode, **kw}).json()["id"]
    return iv, c.post(f"/api/interviews/{iv}/start").json()["question"]

def ans(iv, t, **kw): return c.post(f"/api/interviews/{iv}/answer", json={"transcript": t, "duration": 40, **kw}).json()

def test_health(): assert c.get("/api/health").json()["status"] == "ok"

def test_filler():
    f = analyzers.filler_stats("um I basically like built it, you know", 30)
    assert f["count"] == 4

def test_structure():
    s = analyzers.structure("When the team failed I decided to fix it and the result improved 30%", "behavioral")
    assert "Action" in s["detected"] and "Result" in s["detected"]

def test_json_repair():
    assert parse_json('Sure! {"a": 1, "b": [1,2,],}') == {"a": 1, "b": [1, 2]}
    assert parse_json("nonsense") is None

def test_panel_sequence():
    assert [persona_for("panel", n) for n in range(1, 8)] == ["friendly_hr", "technical_hr", "technical_hr", "strict_manager",
                                                             "friendly_hr", "strict_manager", "technical_hr"]

def test_first_questions_match_persona():
    assert new("friendly_hr")[1]["text"] == "Tell me about yourself."
    assert new("technical_hr")[1]["category"] in {"programming", "dsa", "dbms", "sql", "backend", "frontend", "system_design", "debugging", "projects"}
    assert new("strict_manager")[1]["type"] == "scenario"

def test_manager_progressive_challenge():
    iv, _ = new("strict_manager")
    q2 = ans(iv, "I would discuss with my teammate.")["next"]
    assert q2["follow_up"] and "exactly" in q2["text"]
    q3 = ans(iv, "I would talk to them again and see.")["next"]
    assert q3["follow_up"] and "still" in q3["text"]

def test_technical_followup_uses_candidate_answer():
    iv, _ = new("technical_hr")
    q2 = ans(iv, "I used MongoDB because it is flexible.")["next"]
    assert q2["follow_up"] and "MongoDB" in q2["text"]

def test_friendly_followup_asks_for_action():
    iv, _ = new("friendly_hr")
    q2 = ans(iv, "My project was difficult because I was learning a new technology.")["next"]
    assert q2["follow_up"] and "what did you do" in q2["text"].lower()

def test_no_repeats_across_panel_interview():
    iv, q = new("panel", total=20)
    texts = [q["text"]]
    for _ in range(19):
        r = ans(iv, STRONG)
        if r["done"]: break
        texts.append(r["next"]["text"])
    assert len(texts) == len(set(texts))
    assert all(questions.sim(a, b) < 0.8 for i, a in enumerate(texts) for b in texts[:i])

def test_role_based_questions():
    ml = questions.simulate("AI/ML Engineer")["columns"]["technical_hr"]
    assert {x["category"] for x in ml} <= {"ai_ml", "data_prep", "projects"} and len(ml) == 10
    pm = questions.simulate("Product Manager")["columns"]["technical_hr"]
    assert all(x["category"] in {"product_tech", "analytics"} for x in pm)

def test_resume_questions_differ_per_persona():
    iv = NS(id=1, role="Software Engineer", resume="Developed AI Mock Interview System using LLM.", difficulty="Medium",
            questions=[NS(text="Tell me about yourself.", persona="friendly_hr", follow_up=False, meta={"category": "introduction"}, answer=None)])
    qs = [questions.bank_pick(iv, p, "medium", random.Random(1))["question"] for p in ("technical_hr", "strict_manager", "friendly_hr")]
    assert all("AI Mock Interview System" in q for q in qs) and len(set(qs)) == 3

def test_difficulty_adapts():
    good = {"content": 95, "communication": 90, "confidence": 85, "structure": {"score": 90}}
    bad = {"content": 20, "communication": 30, "confidence": 30, "structure": {"score": 10}}
    iv = NS(difficulty="Medium")
    assert questions.target_difficulty(iv, good) == "hard" and questions.target_difficulty(iv, bad) == "easy"

def test_persona_diversity():
    for role in ("Software Engineer", "AI/ML Engineer", "Product Manager", "Data Analyst"):
        m = questions.simulate(role)["metrics"]
        assert m["duplicates"] == 0 and m["category_overlap"] == 0 and m["persona_mismatch"] == 0 and m["diversity_score"] >= 90
    assert c.get("/api/dev/persona-diversity").json()["metrics"]["diversity_score"] >= 90

def test_flow_report_history_delete():
    iv, _ = new("panel", total=3)
    assert ans(iv, "")["detail"].startswith("Empty")
    ans(iv, STRONG); ans(iv, "I dunno maybe")
    assert ans(iv, "", skipped=True)["done"]
    assert c.post(f"/api/interviews/{iv}/answer", json={"transcript": "hello there"}).status_code == 409
    rep = c.get(f"/api/interviews/{iv}/report").json()
    assert rep["questions"] and 0 <= rep["overall"] <= 100
    assert c.delete(f"/api/interviews/{iv}").json()["deleted"] == iv
