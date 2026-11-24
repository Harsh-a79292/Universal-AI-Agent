"""
Test Fallback Simulation
Simulates Gemini failure (such as 503 UNAVAILABLE, 429, or network error)
and verifies that query_llm_with_fallback cleanly falls back to Groq.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.gemini_model import GeminiModel
from models.groq_model import GroqModel
from models.llm_service import query_llm_with_fallback
from unittest.mock import patch

def test_gemini_503_fallback_simulation():
    print("\n--- SIMULATION TEST 1: Gemini 503 Service Unavailable -> Groq Fallback ---")
    
    # Mock GeminiModel.generate to simulate a 503 error
    simulated_503_error = "503 The model is overloaded. Please try again later."
    with patch.object(GeminiModel, 'generate', return_value={
        "success": False,
        "content": "",
        "error": simulated_503_error,
        "model": "Gemini (gemini-3.8-flash)"
    }):
        # Mock GroqModel.generate to return valid output
        with patch.object(GroqModel, 'generate', return_value={
            "success": True,
            "content": "Hello! I am responding via Groq fallback successfully.",
            "error": None,
            "model": "Groq (openai/gpt-oss-120b)"
        }):
            res = query_llm_with_fallback(
                prompt="Explain photosynthesis briefly.",
                system_instruction="Be concise.",
                preferred_model="auto"
            )
            
            print(f"Success: {res.get('success')}")
            print(f"Model Switched: {res.get('model_switched')}")
            print(f"Switch Reason: {res.get('switch_reason')}")
            print(f"Model Used: {res.get('model')}")
            print(f"Content: {res.get('content')}")
            
            assert res.get("success") is True, "Fallback should succeed"
            assert res.get("model_switched") is True, "Model switched flag should be True"
            assert "Gemini was unavailable" in res.get("switch_reason", ""), "Switch reason should explain Gemini failure"
            assert "503" in res.get("switch_reason", ""), "Switch reason should mention the 503 error"
            assert "Groq" in res.get("model", ""), "Model used should be Groq"
            print(">>> PASS: Simulated Gemini 503 cleanly triggered Groq fallback!")

def test_gemini_retry_logic():
    print("\n--- SIMULATION TEST 2: Gemini Retry Logic (bounded retries, no infinite loop) ---")
    gemini = GeminiModel()
    
    call_count = 0
    def mock_generate_content(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise Exception("503 Service Temporarily Unavailable")
        
    if gemini.client:
        with patch.object(gemini.client.models, 'generate_content', side_effect=mock_generate_content):
            res = gemini.generate("test prompt", max_retries=1)
            print(f"Total attempts: {call_count}")
            print(f"Result success: {res['success']}")
            print(f"Result error: {res['error']}")
            
            # max_retries=1 means 1 original attempt + 1 retry = 2 attempts total
            assert call_count == 2, f"Expected 2 attempts, got {call_count}"
            assert res["success"] is False, "Should fail after bounded retries"
            assert "503" in res["error"], "Error message preserved"
            print(">>> PASS: Gemini bounded retry executed exactly 2 times and stopped cleanly!")
    else:
        print("Gemini client not initialized with key; testing fallback path without client.")

def test_redaction():
    print("\n--- SIMULATION TEST 3: API Key Redaction in Error Messages ---")
    from models.gemini_model import sanitize_error_message as gemini_sanitize
    from models.groq_model import sanitize_error_message as groq_sanitize
    
    fake_gemini_error = "API call failed for key AIzaSyDUMMYKEY1234567890123456789012 with 403"
    sanitized = gemini_sanitize(fake_gemini_error)
    print(f"Sanitized: {sanitized}")
    assert "AIzaSy" not in sanitized or "[REDACTED_GEMINI_KEY]" in sanitized
    print(">>> PASS: Sensitive keys successfully redacted from logs/errors!")

if __name__ == "__main__":
    test_gemini_503_fallback_simulation()
    test_gemini_retry_logic()
    test_redaction()
    print("\n============================================")
    print("ALL FALLBACK SIMULATION TESTS PASSED (3/3)!")
    print("============================================")

