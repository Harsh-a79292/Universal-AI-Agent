import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file explicitly if present locally
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

def _get_secret_or_env(key: str, default: str = "") -> str:
    """Read from environment variable or streamlit secrets if deployed on Streamlit Cloud."""
    val = os.getenv(key, "")
    if not val:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and key in st.secrets:
                val = str(st.secrets[key])
        except Exception:
            pass
    return val.strip() if val else default

class Settings:
    # API Keys (Loaded from .env locally or Streamlit Cloud Secrets)
    GEMINI_API_KEY: str = _get_secret_or_env("GEMINI_API_KEY")
    GROQ_API_KEY: str = _get_secret_or_env("GROQ_API_KEY")
    TAVILY_API_KEY: str = _get_secret_or_env("TAVILY_API_KEY")

    # Recommended Model IDs (Current active models)
    DEFAULT_GEMINI_MODEL: str = "gemini-3.8-flash"
    DEFAULT_GROQ_MODEL: str = "openai/gpt-oss-120b"

    # SQLite Database
    DB_PATH: Path = BASE_DIR / "database" / "chat_history.db"

    @classmethod
    def reload(cls):
        """Reload environment variables if changed in runtime."""
        if ENV_PATH.exists():
            load_dotenv(dotenv_path=ENV_PATH, override=True)
        cls.GEMINI_API_KEY = _get_secret_or_env("GEMINI_API_KEY")
        cls.GROQ_API_KEY = _get_secret_or_env("GROQ_API_KEY")
        cls.TAVILY_API_KEY = _get_secret_or_env("TAVILY_API_KEY")

    @classmethod
    def validate_keys(cls) -> dict:
        """Check status of required keys without revealing their values."""
        return {
            "gemini": bool(cls.GEMINI_API_KEY),
            "groq": bool(cls.GROQ_API_KEY),
            "tavily": bool(cls.TAVILY_API_KEY),
        }

settings = Settings()

