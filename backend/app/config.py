import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    el_key = os.getenv("ELEVENLABS_API_KEY", "")
    el_voice = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    db = os.getenv("DATABASE_URL", "sqlite:///./interview.db")
    demo = os.getenv("DEMO_MODE", "true").lower() == "true"
    whisper = os.getenv("WHISPER_MODEL", "base")
    cors = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

settings = Settings()
settings.sim = float(os.getenv("QUESTION_SIMILARITY_THRESHOLD", "0.80"))
