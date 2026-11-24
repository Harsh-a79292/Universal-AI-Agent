import re
from typing import Optional, Dict, Any, List
from groq import Groq
from config.settings import settings

def sanitize_error_message(error_str: str) -> str:
    """Strip potential sensitive tokens or keys from error strings."""
    if not error_str:
        return ""
    clean = re.sub(r'gsk_[A-Za-z0-9_-]{15,}', '[REDACTED_GROQ_KEY]', error_str)
    clean = re.sub(r'AIzaSy[A-Za-z0-9_-]{10,}', '[REDACTED_GEMINI_KEY]', clean)
    clean = re.sub(r'tvly-[A-Za-z0-9_-]{15,}', '[REDACTED_TAVILY_KEY]', clean)
    return clean

class GroqModel:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.DEFAULT_GROQ_MODEL
        self.api_key = settings.GROQ_API_KEY
        self.client = None
        if self.api_key:
            self.client = Groq(api_key=self.api_key)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate response using Groq SDK.
        Returns a dictionary with success, content, and error details.
        """
        if not self.is_configured():
            return {
                "success": False,
                "content": "",
                "error": "Groq API key is not configured.",
                "model": self.model_name
            }

        try:
            messages: List[Dict[str, str]] = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.4,
                max_tokens=2500
            )

            text = response.choices[0].message.content or ""
            return {
                "success": True,
                "content": text,
                "error": None,
                "model": f"Groq ({self.model_name})"
            }
        except Exception as e:
            return {
                "success": False,
                "content": "",
                "error": sanitize_error_message(str(e)),
                "model": f"Groq ({self.model_name})"
            }
