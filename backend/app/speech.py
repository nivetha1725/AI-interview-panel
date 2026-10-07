"""STT (faster-whisper, lazy) and TTS (ElevenLabs) with graceful failure."""
import tempfile, os
import httpx
from fastapi import HTTPException
from .config import settings

_model = None

def transcribe_file(data: bytes, suffix=".webm"):
    global _model
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise HTTPException(503, "Whisper is not installed. Type your answer, use Chrome live transcript, or `pip install faster-whisper`.")
    if _model is None: _model = WhisperModel(settings.whisper, compute_type="int8")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data); path = f.name
    try:
        segs, info = _model.transcribe(path)
        text = " ".join(s.text.strip() for s in segs).strip()
        return {"transcript": text, "duration": round(info.duration, 1)}
    except Exception:
        raise HTTPException(422, "Could not read that audio. Please record again or type your answer.")
    finally:
        os.unlink(path)

async def tts(text: str) -> bytes:
    if not settings.el_key:
        raise HTTPException(501, "ElevenLabs not configured; using browser speech.")
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"https://api.elevenlabs.io/v1/text-to-speech/{settings.el_voice}",
                             headers={"xi-api-key": settings.el_key}, json={"text": text[:1000]})
            r.raise_for_status()
            return r.content
    except Exception:
        raise HTTPException(502, "ElevenLabs is unavailable; using browser speech.")
