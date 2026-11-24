from typing import Dict, Any, Optional
from models.gemini_model import GeminiModel
from models.groq_model import GroqModel

def query_llm_with_fallback(prompt: str, system_instruction: str, preferred_model: str = "auto") -> Dict[str, Any]:
    """
    Execute LLM call using Gemini as primary and Groq as fallback,
    or honoring the user's manual preference. Informative if switched.
    """
    gemini = GeminiModel()
    groq = GroqModel()

    def call_gemini():
        res = gemini.generate(prompt, system_instruction=system_instruction)
        return res

    def call_groq():
        res = groq.generate(prompt, system_instruction=system_instruction)
        return res

    if preferred_model == "groq":
        res = call_groq()
        if res.get("success"):
            return {**res, "model_switched": False, "switch_reason": ""}
        # Fallback to Gemini if groq failed
        fallback_res = call_gemini()
        return {
            **fallback_res,
            "model_switched": True,
            "switch_reason": f"Preferred model Groq encountered an error ({res.get('error')}). Switched to Gemini."
        }
    elif preferred_model == "gemini":
        res = call_gemini()
        if res.get("success"):
            return {**res, "model_switched": False, "switch_reason": ""}
        # Fallback to Groq
        fallback_res = call_groq()
        return {
            **fallback_res,
            "model_switched": True,
            "switch_reason": f"Preferred model Gemini encountered an error ({res.get('error')}). Switched to Groq."
        }
    else:
        # Default Auto: Primary Gemini -> Fallback Groq
        res = call_gemini()
        if res.get("success"):
            return {**res, "model_switched": False, "switch_reason": ""}
        
        fallback_res = call_groq()
        if fallback_res.get("success"):
            return {
                **fallback_res,
                "model_switched": True,
                "switch_reason": f"Gemini was unavailable ({res.get('error')}). Automatically fell back to Groq."
            }
        
        return {
            "success": False,
            "content": "",
            "error": f"Both primary and fallback models failed. (Gemini: {res.get('error')} | Groq: {fallback_res.get('error')})",
            "model": "None",
            "model_switched": False,
            "switch_reason": ""
        }

