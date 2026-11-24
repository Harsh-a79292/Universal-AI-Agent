from typing import Dict, Any, Optional
from models.llm_service import query_llm_with_fallback

def generate_code_solution(requirement: str, language: str = "Python", preferred_model: str = "auto") -> Dict[str, Any]:
    """Generate robust, production-quality code based on user prompt."""
    prompt = f"""Language: {language}
Requirement:
{requirement}

Instructions:
1. Write clean, idiomatic, well-commented {language} code.
2. Include error handling and type hints where applicable.
3. Provide a brief explanation of how the code works and an example usage snippet.
4. Do NOT execute code, output pure markdown format."""
    system_instruction = f"You are an expert software engineer specializing in {language}."
    return query_llm_with_fallback(prompt, system_instruction, preferred_model=preferred_model)

def explain_code_snippet(code: str, language: str = "Python", preferred_model: str = "auto") -> Dict[str, Any]:
    """Provide a structured explanation of existing code."""
    prompt = f"""Language: {language}
Code to explain:
```{language}
{code}
```

Instructions:
1. Overview: What does this code do?
2. Line-by-line or section-by-section breakdown.
3. Time and space complexity if applicable.
4. Potential edge cases."""
    system_instruction = "You are a master code mentor and architect."
    return query_llm_with_fallback(prompt, system_instruction, preferred_model=preferred_model)

def debug_code_error(code: str, error_message: str, language: str = "Python", preferred_model: str = "auto") -> Dict[str, Any]:
    """Debug code when provided with error traceback and propose fixes."""
    prompt = f"""Language: {language}

Buggy Code:
```{language}
{code}
```

Error Traceback / Issue:
{error_message}

Instructions:
1. Identify the root cause of the error.
2. Provide the corrected, working code.
3. Explain exactly what changes were made and why."""
    system_instruction = "You are a debugging expert. Be precise and identify root causes."
    return query_llm_with_fallback(prompt, system_instruction, preferred_model=preferred_model)

