import time
import re
from typing import Optional, Dict, Any, List
from google import genai
from config.settings import settings

def sanitize_error_message(error_str: str) -> str:
    """Strip potential sensitive tokens or keys from error strings."""
    if not error_str:
        return ""
    # Mask key-like strings
    clean = re.sub(r'AIzaSy[A-Za-z0-9_-]{10,}', '[REDACTED_GEMINI_KEY]', error_str)
    clean = re.sub(r'gsk_[A-Za-z0-9_-]{15,}', '[REDACTED_GROQ_KEY]', clean)
    clean = re.sub(r'tvly-[A-Za-z0-9_-]{15,}', '[REDACTED_TAVILY_KEY]', clean)
    return clean

class GeminiModel:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.DEFAULT_GEMINI_MODEL
        self.api_key = settings.GEMINI_API_KEY
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def generate(self, prompt: str, system_instruction: Optional[str] = None, max_retries: int = 1) -> Dict[str, Any]:
        """
        Generate response using google-genai SDK.
        Includes bounded retry handling for transient 503 / 429 server errors
        before cleanly returning error for Groq fallback.
        Never exposes API keys in logs or errors.
        """
        if not self.is_configured():
            return {
                "success": False,
                "content": "",
                "error": "Gemini API key is not configured.",
                "model": self.model_name
            }

        config = {}
        if system_instruction:
            config["system_instruction"] = system_instruction

        last_error = ""
        # Up to max_retries + 1 total attempts (e.g. 1 attempt + 1 retry = 2 max)
        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config if config else None
                )

                text = response.text or ""
                return {
                    "success": True,
                    "content": text,
                    "error": None,
                    "model": f"Gemini ({self.model_name})"
                }
            except Exception as e:
                err_str = sanitize_error_message(str(e))
                last_error = err_str
                # Check if it's a transient server overload (503 / 429 / resource exhausted / unavailable)
                transient_indicators = ["503", "429", "unavailable", "resource exhausted", "overloaded"]
                is_transient = any(ind in err_str.lower() for ind in transient_indicators)
                
                if is_transient and attempt < max_retries:
                    # Short sensible backoff (1.5s), never infinite
                    time.sleep(1.5)
                    continue
                else:
                    break

        return {
            "success": False,
            "content": "",
            "error": last_error,
            "model": f"Gemini ({self.model_name})"
        }
