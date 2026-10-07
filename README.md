# AI Mock Interview Panel — Multi-Persona Voice Agent
One local LLM (Ollama) plays three interviewers — Technical HR, Strict Manager, Friendly HR (or all three as a panel) —
asks adaptive follow-ups, listens to your voice answers, scores them and produces a report.

## Run
```bash
cd backend
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # DEMO_MODE=true works with no AI services
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000 (the UI is served by FastAPI). API docs: http://localhost:8000/docs

## Real AI mode
1. Install Ollama, then `ollama pull llama3.1:8b`; set `DEMO_MODE=false` in `.env`.
2. Whisper (optional): `pip install faster-whisper` (model set by `WHISPER_MODEL`). Without it, Chrome's live transcript / typing still works.
3. ElevenLabs (optional): set `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID`; otherwise browser speech is used.

## Demo mode
`DEMO_MODE=true`: if Ollama is unreachable, the 8-question sample interview and follow-up rules are used; analytics are deterministic.

## Tests
`cd backend && python -m pytest`

## Layout
`app/personas.py` personas + demo bank · `app/llm.py` prompts, Ollama, JSON repair · `app/analyzers.py` fillers/structure/tone/scores ·
`app/speech.py` Whisper + ElevenLabs · `app/main.py` routes + state machine · `app/db.py` SQLAlchemy models · `app/static/index.html` UI.

## Troubleshooting
- "Ollama unavailable": run `ollama serve`, check `OLLAMA_MODEL`, or use `DEMO_MODE=true`.
- "Microphone blocked": allow mic access (needs localhost/HTTPS); or type your answer.
- "Whisper is not installed": `pip install faster-whisper`.

## Persona / question-generation architecture
One LLM, three interviewer "brains" (`app/personas.py`): each persona has its own system prompt, evaluation criteria, follow-up
strategy, difficulty strategy and question bank (`app/question_bank/{technical,manager,friendly_hr}.json`, one file per persona,
entries `[category, question, difficulty, roles]`). `app/questions.py` decides every next question:

1. **Persona**: single mode, or panel order Friendly -> Technical -> Technical -> Manager -> Friendly -> Manager -> Technical, then cycling.
2. **Follow-up or fresh?** Only within the same persona's thread, driven by the previous answer's score:
   Technical drills into technologies the candidate named ("You mentioned MongoDB..."), Manager escalates (what first -> what if it fails -> two-hour deadline),
   Friendly asks for the missing Action/Result ("what did you do", "what did you learn").
3. **Difficulty**: score > 80 -> hard, 50-80 -> medium, < 50 -> easy (plus a clarifying follow-up). Persona never changes because of score.
4. **Fresh question**: role-filtered (Software / AI-ML / Data / Product), persona-owned categories only, unused categories first;
   if a resume is present each persona asks its own angle on the same project (architecture / live-demo failure / motivation).
5. **LLM adaptation**: the seed is sent to Ollama with the persona prompt and the full asked-questions list; the reply is accepted only if it passes validation.
6. **Anti-repetition**: reject if similarity to any earlier question >= `QUESTION_SIMILARITY_THRESHOLD` (default 0.80) or if its category was already used
   by another persona. Similarity is lexical (stemmed-word cosine), not an embedding model. `Question.meta` stores category, purpose and max similarity.

**Test Persona Diversity** (button in the nav, or `GET /api/dev/persona-diversity?role=...`) generates 10 questions per persona into one shared history and reports
duplicates, similar pairs, category overlap, intent overlap, persona mismatch and a 0-100 diversity score.

Existing `interview.db` files are migrated automatically (new `meta` column).
