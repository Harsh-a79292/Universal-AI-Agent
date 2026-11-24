"""Real API test — run outside sandbox."""
import sys
sys.path.insert(0, ".")

from models.gemini_model import GeminiModel
from models.groq_model import GroqModel
from tools.search import search_tavily
from agent.core import UniversalAgent

print("=== REAL API TESTS ===\n")
results = []

# Gemini
try:
    m = GeminiModel()
    r = m.generate("Reply with exactly: GEMINI_OK", system_instruction="Reply only with GEMINI_OK.")
    if r.get("success") and "GEMINI_OK" in r.get("content",""):
        msg = "PASS  Gemini API: " + r["content"][:60]
        results.append(("PASS", "Gemini API direct call"))
    else:
        msg = "FAIL  Gemini API: " + str(r.get("error","Unknown"))
        results.append(("FAIL", "Gemini API direct call", r.get("error","")))
    print(msg)
except Exception as e:
    print(f"FAIL  Gemini API: {e}")
    results.append(("FAIL", "Gemini API direct call", str(e)))

# Groq
try:
    m = GroqModel()
    r = m.generate("Reply with exactly: GROQ_OK", system_instruction="Reply only with GROQ_OK.")
    if r.get("success") and "GROQ_OK" in r.get("content",""):
        msg = "PASS  Groq API: " + r["content"][:60]
        results.append(("PASS", "Groq API direct call"))
    else:
        msg = "FAIL  Groq API: " + str(r.get("error","Unknown"))
        results.append(("FAIL", "Groq API direct call", r.get("error","")))
    print(msg)
except Exception as e:
    print(f"FAIL  Groq API: {e}")
    results.append(("FAIL", "Groq API direct call", str(e)))

# Tavily
try:
    r = search_tavily("Python 3 latest features", max_results=3)
    if r.get("success") and len(r.get("results",[])) > 0:
        title = r["results"][0]["title"][:60]
        print(f"PASS  Tavily Search: {len(r['results'])} results. First: {title}")
        results.append(("PASS", "Tavily Web Search"))
    else:
        err = str(r.get("error","Unknown"))
        print(f"FAIL  Tavily Search: {err}")
        results.append(("FAIL", "Tavily Web Search", err))
except Exception as e:
    print(f"FAIL  Tavily Search: {e}")
    results.append(("FAIL", "Tavily Web Search", str(e)))

# LangGraph Agent - simple direct answer
try:
    agent = UniversalAgent()
    result = agent.run("What is the capital of France?", memory_enabled=False)
    if result.get("response") and "Paris" in result["response"]:
        print(f"PASS  LangGraph Agent: Capital of France = Paris. Model: {result.get('model_used')}")
        results.append(("PASS", "LangGraph Agent direct answer"))
    else:
        print(f"FAIL  LangGraph Agent: {result.get('response','')[:100]}")
        results.append(("FAIL", "LangGraph Agent direct answer", result.get("response","")[:100]))
except Exception as e:
    print(f"FAIL  LangGraph Agent: {e}")
    results.append(("FAIL", "LangGraph Agent direct answer", str(e)))

# LangGraph Agent - calculator
try:
    agent = UniversalAgent()
    result = agent.run("Use the calculator tool: sqrt(225) + 100 / 4", memory_enabled=False)
    resp = result.get("response","")
    tools_used = [t["tool_name"] for t in result.get("tool_history",[])]
    if "40" in resp and "calculator" in tools_used:
        print(f"PASS  LangGraph Agent + Calculator: got 40 in response. Tools: {tools_used}")
        results.append(("PASS", "LangGraph Agent + Calculator tool"))
    else:
        print(f"FAIL  LangGraph Agent + Calculator: resp={resp[:100]}, tools={tools_used}")
        results.append(("FAIL", "LangGraph Agent + Calculator tool", resp[:100]))
except Exception as e:
    print(f"FAIL  LangGraph Agent + Calculator: {e}")
    results.append(("FAIL", "LangGraph Agent + Calculator tool", str(e)))

print("\n=== SUMMARY ===")
passed = [r for r in results if r[0]=="PASS"]
failed = [r for r in results if r[0]=="FAIL"]
print(f"PASS: {len(passed)}  FAIL: {len(failed)}")
for r in results:
    icon = "PASS" if r[0]=="PASS" else "FAIL"
    print(f"  {icon}  {r[1]}")

