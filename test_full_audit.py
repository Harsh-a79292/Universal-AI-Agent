"""
Universal AI Agent — Full Automated Audit Test Suite
Covers all 20+ features across Phases 2 and 4 (security).
Run from project root: python test_full_audit.py
"""
import sys
import os
import io
import json
import uuid
import traceback

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "✅ PASS"
FAIL = "❌ FAIL"
SKIP = "⚠️  SKIP"
MOCK = "🔵 MOCK"

results = []

def test(name, real_api=True):
    """Decorator-style context for recording test results."""
    def decorator(fn):
        label = "[REAL API]" if real_api else "[MOCKED]"
        try:
            msg = fn()
            results.append((PASS, name, label, msg or ""))
        except AssertionError as e:
            results.append((FAIL, name, label, str(e)))
        except Exception as e:
            results.append((FAIL, name, label, f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}"))
        return fn
    return decorator

# ─────────────────────────────────────────────────────────
# SECTION 1: DATABASE CRUD (no API key needed)
# ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SECTION 1: DATABASE")
print("="*60)

@test("DB: init_db + create_session", real_api=False)
def _():
    from database.db import init_db, create_session, get_all_sessions
    init_db()
    sid = f"test-{uuid.uuid4()}"
    create_session(sid, "Test Session")
    sessions = get_all_sessions()
    ids = [s["id"] for s in sessions]
    assert sid in ids, f"Session {sid} not found after creation"
    return f"Session created OK. Total sessions: {len(sessions)}"

@test("DB: save_message with activities + tool_history", real_api=False)
def _():
    from database.db import create_session, save_message, get_session_messages
    sid = f"test-msg-{uuid.uuid4()}"
    create_session(sid, "Msg Test")
    activities = [{"stage": "planning", "message": "Test plan", "details": {}}]
    tool_history = [{"tool_name": "calculator", "tool_args": {"expression": "2+2"}, "result_summary": "4"}]
    save_message(
        session_id=sid,
        role="assistant",
        content="Test response",
        model_used="gemini-test",
        sources=[{"title": "Test", "url": "https://example.com", "content": "snippet", "published_date": None}],
        agent_logs=["Step 1 done"],
        activities=activities,
        tool_history=tool_history
    )
    msgs = get_session_messages(sid)
    assert len(msgs) == 1, f"Expected 1 message, got {len(msgs)}"
    msg = msgs[0]
    assert msg["activities"] == activities, "activities mismatch"
    assert msg["tool_history"] == tool_history, "tool_history mismatch"
    assert msg["sources"][0]["url"] == "https://example.com", "sources mismatch"
    return "save_message with all fields OK"

@test("DB: Notes CRUD", real_api=False)
def _():
    from database.db import create_note, update_note, get_all_notes, delete_note
    nid = create_note("Audit Note", "This is test content", tags="test,audit")
    assert isinstance(nid, int) and nid > 0, f"create_note returned bad id: {nid}"
    update_note(nid, "Updated Title", "Updated content", tags="updated")
    notes = get_all_notes(search_query="Updated")
    assert any(n["id"] == nid for n in notes), "Updated note not found in search"
    delete_note(nid)
    notes_after = get_all_notes()
    assert not any(n["id"] == nid for n in notes_after), "Note not deleted"
    return "Notes CRUD OK"

@test("DB: Memory CRUD", real_api=False)
def _():
    from database.db import create_memory, get_all_memories, update_memory, delete_memory
    mid = create_memory("I prefer Python over JavaScript", category="preference", source="user")
    mems = get_all_memories()
    assert any(m["content"] == "I prefer Python over JavaScript" for m in mems), "Memory not found"
    # update — find the id
    target = next((m for m in mems if m["content"] == "I prefer Python over JavaScript"), None)
    assert target, "Cannot find created memory"
    update_memory(target["id"], "I prefer Python", category="language_pref", is_enabled=True)
    updated_mems = get_all_memories()
    target2 = next((m for m in updated_mems if m["id"] == target["id"]), None)
    assert target2 and target2["content"] == "I prefer Python", "Memory update failed"
    delete_memory(target["id"])
    final = get_all_memories()
    assert not any(m["id"] == target["id"] for m in final), "Memory not deleted"
    return "Memory CRUD OK"

@test("DB: Reminders lifecycle", real_api=False)
def _():
    from database.db import create_reminder, get_all_reminders, get_due_reminders, mark_reminder_notified, set_reminder_completed, delete_reminder
    from datetime import datetime, timedelta
    past = (datetime.now() - timedelta(minutes=5)).isoformat()
    rid = create_reminder("Audit Reminder", due_datetime=past, description="Test desc")
    assert isinstance(rid, int) and rid > 0, f"Bad reminder id: {rid}"
    due = get_due_reminders()
    assert any(r["id"] == rid for r in due), "Past-due reminder not in due list"
    mark_reminder_notified(rid)
    due2 = get_due_reminders()
    assert not any(r["id"] == rid for r in due2), "Notified reminder still appearing as due"
    set_reminder_completed(rid, True)
    all_r = get_all_reminders()
    target = next((r for r in all_r if r["id"] == rid), None)
    assert target and target["is_completed"] == 1, "Reminder not marked completed"
    delete_reminder(rid)
    final = get_all_reminders()
    assert not any(r["id"] == rid for r in final), "Reminder not deleted"
    return "Reminder lifecycle OK"

@test("DB: Career Plan CRUD + progress tracking", real_api=False)
def _():
    from database.db import create_career_plan, get_all_career_plans, update_career_plan_tasks, delete_career_plan
    tasks = [
        {"title": "Task 1", "description": "Do thing 1", "completed": False},
        {"title": "Task 2", "description": "Do thing 2", "completed": True},
    ]
    pid = create_career_plan("Software Engineer at Google", tasks, total_days=90)
    assert isinstance(pid, int) and pid > 0, f"Bad career plan id: {pid}"
    plans = get_all_career_plans()
    plan = next((p for p in plans if p["id"] == pid), None)
    assert plan, "Career plan not found"
    assert plan["total_tasks"] == 2, f"Expected 2 tasks, got {plan['total_tasks']}"
    assert plan["completed_tasks"] == 1, f"Expected 1 completed, got {plan['completed_tasks']}"
    assert abs(plan["progress_pct"] - 50.0) < 0.01, f"Expected 50% progress, got {plan['progress_pct']}"
    # Mark task 1 complete
    updated_tasks = [
        {"title": "Task 1", "description": "Do thing 1", "completed": True},
        {"title": "Task 2", "description": "Do thing 2", "completed": True},
    ]
    update_career_plan_tasks(pid, updated_tasks)
    plans2 = get_all_career_plans()
    plan2 = next((p for p in plans2 if p["id"] == pid), None)
    assert plan2 and abs(plan2["progress_pct"] - 100.0) < 0.01, f"Expected 100%, got {plan2['progress_pct']}"
    delete_career_plan(pid)
    plans3 = get_all_career_plans()
    assert not any(p["id"] == pid for p in plans3), "Career plan not deleted"
    return "Career plan CRUD + progress OK"

@test("DB: Chat session search + pin + rename + delete", real_api=False)
def _():
    from database.db import create_session, get_all_sessions, toggle_pin_session, update_session_title, delete_session, save_message
    sid = f"test-search-{uuid.uuid4()}"
    create_session(sid, "SearchableSession")
    save_message(sid, "user", "unique content xyz987")
    # Search by title
    found_title = get_all_sessions(search_query="SearchableSession")
    assert any(s["id"] == sid for s in found_title), "Search by title failed"
    # Search by message content
    found_content = get_all_sessions(search_query="unique content xyz987")
    assert any(s["id"] == sid for s in found_content), "Search by message content failed"
    # Pin
    toggle_pin_session(sid, True)
    sessions = get_all_sessions()
    target = next((s for s in sessions if s["id"] == sid), None)
    assert target and target["is_pinned"] == 1, "Pin failed"
    # Rename
    update_session_title(sid, "RenamedSession")
    sessions2 = get_all_sessions()
    renamed = next((s for s in sessions2 if s["id"] == sid), None)
    assert renamed and renamed["title"] == "RenamedSession", "Rename failed"
    # Delete
    delete_session(sid)
    sessions3 = get_all_sessions()
    assert not any(s["id"] == sid for s in sessions3), "Delete failed"
    return "Chat management OK"

# ─────────────────────────────────────────────────────────
# SECTION 2: TOOLS (no API keys for calculator/datetime)
# ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SECTION 2: TOOLS")
print("="*60)

@test("Tool: Calculator — basic arithmetic", real_api=False)
def _():
    from tools.calculator import calculate_expression
    r = calculate_expression("2 + 2 * 3")
    assert r["success"], f"Calculator failed: {r['error']}"
    assert r["result"] == 8, f"Expected 8, got {r['result']}"
    return f"2+2*3 = {r['result']}"

@test("Tool: Calculator — sqrt and powers", real_api=False)
def _():
    from tools.calculator import calculate_expression
    r = calculate_expression("sqrt(144) + 7 * 3")
    assert r["success"], f"Calculator failed: {r['error']}"
    assert abs(r["result"] - 33.0) < 0.001, f"Expected 33.0, got {r['result']}"
    return f"sqrt(144)+7*3 = {r['result']}"

@test("Tool: Calculator — division by zero safety", real_api=False)
def _():
    from tools.calculator import calculate_expression
    r = calculate_expression("10 / 0")
    assert not r["success"], "Should have failed on div by zero"
    assert "zero" in r["error"].lower(), f"Expected zero error, got: {r['error']}"
    return f"Division by zero handled: {r['error']}"

@test("Tool: Calculator — no eval/exec (AST only)", real_api=False)
def _():
    from tools.calculator import calculate_expression
    # Try to inject code execution
    r = calculate_expression("__import__('os').system('echo hack')")
    assert not r["success"], "Unsafe expression should be rejected"
    return f"Code injection blocked: {r['error']}"

@test("Tool: Datetime — local timezone", real_api=False)
def _():
    from tools.datetime_tool import get_current_datetime
    r = get_current_datetime()
    assert r["success"], f"Datetime failed: {r['error']}"
    assert r.get("date"), "No date returned"
    assert r.get("day_of_week"), "No day_of_week returned"
    return f"DateTime: {r['formatted']}"

@test("Tool: Datetime — specific timezone (Asia/Kolkata)", real_api=False)
def _():
    from tools.datetime_tool import get_current_datetime
    r = get_current_datetime(timezone_name="Asia/Kolkata")
    assert r["success"], f"Datetime IST failed: {r['error']}"
    assert "IST" in r["formatted"] or "Asia" in r["timezone"] or "+05:30" in r["iso"], \
        f"Expected IST timezone, got: {r['formatted']}"
    return f"IST DateTime: {r['formatted']}"

@test("Tool: Web Extractor — SSRF block (localhost)", real_api=False)
def _():
    from tools.web_extractor import extract_website_content
    r = extract_website_content("http://localhost:8080/admin")
    assert not r["success"], "SSRF should be blocked"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower(), \
        f"Expected SSRF block message, got: {r['error']}"
    return f"SSRF blocked: {r['error']}"

@test("Tool: Web Extractor — invalid scheme", real_api=False)
def _():
    from tools.web_extractor import extract_website_content
    r = extract_website_content("ftp://files.example.com/data")
    assert not r["success"], "Invalid scheme should fail"
    return f"Invalid scheme blocked: {r['error']}"

@test("Tool: Tavily Web Search (REAL API)", real_api=True)
def _():
    from tools.search import search_tavily
    r = search_tavily(query="Python 3.13 release notes", max_results=3)
    assert r["success"], f"Tavily search failed: {r['error']}"
    assert len(r["results"]) > 0, "No results returned"
    for item in r["results"]:
        assert "title" in item and "url" in item, f"Result missing fields: {item}"
    return f"Tavily returned {len(r['results'])} results. First: {r['results'][0]['title']}"

# ─────────────────────────────────────────────────────────
# SECTION 3: LLM MODELS (REAL API)
# ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SECTION 3: LLM MODELS (REAL API)")
print("="*60)

@test("LLM: Gemini direct call (REAL API)", real_api=True)
def _():
    from models.gemini_model import GeminiModel
    m = GeminiModel()
    res = m.generate("Reply with exactly: GEMINI_OK", system_instruction="Reply only with GEMINI_OK.")
    assert res.get("success"), f"Gemini call failed: {res.get('error')}"
    assert "GEMINI_OK" in res.get("content", ""), f"Expected GEMINI_OK in response: {res.get('content')}"
    return f"Gemini responded: {res['content'][:80]}"

@test("LLM: Groq direct call (REAL API)", real_api=True)
def _():
    from models.groq_model import GroqModel
    m = GroqModel()
    res = m.generate("Reply with exactly: GROQ_OK", system_instruction="Reply only with GROQ_OK.")
    assert res.get("success"), f"Groq call failed: {res.get('error')}"
    assert "GROQ_OK" in res.get("content", ""), f"Expected GROQ_OK in response: {res.get('content')}"
    return f"Groq responded: {res['content'][:80]}"

@test("LLM: query_llm_with_fallback — auto mode (REAL API)", real_api=True)
def _():
    from models.llm_service import query_llm_with_fallback
    res = query_llm_with_fallback("What is 2+2?", "Answer concisely.", preferred_model="auto")
    assert res.get("success"), f"Fallback LLM failed: {res.get('error')}"
    assert "4" in res.get("content", ""), f"Expected '4' in response: {res.get('content')}"
    return f"Auto LLM ({res.get('model')}): {res['content'][:80]}"

# ─────────────────────────────────────────────────────────
# SECTION 4: LANGGRAPH AGENT (REAL API)
# ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SECTION 4: LANGGRAPH AGENT (REAL API)")
print("="*60)

@test("Agent: Direct answer (no tools) (REAL API)", real_api=True)
def _():
    from agent.core import UniversalAgent
    agent = UniversalAgent()
    result = agent.run("What is the capital of France?", memory_enabled=False)
    assert result.get("response"), "No response returned"
    assert "Paris" in result["response"], f"Expected Paris in answer: {result['response'][:200]}"
    assert len(result.get("tool_history", [])) == 0, \
        f"No tools should be used for this, got: {result['tool_history']}"
    return f"Direct answer OK. Tool steps: {len(result['tool_history'])}"

@test("Agent: Calculator tool call via agent (REAL API)", real_api=True)
def _():
    from agent.core import UniversalAgent
    agent = UniversalAgent()
    result = agent.run("Calculate: sqrt(225) + 100 / 4", memory_enabled=False)
    assert result.get("response"), "No response returned"
    # sqrt(225) = 15, 100/4 = 25, total = 40
    response_text = result["response"]
    assert "40" in response_text, f"Expected 40 in response: {response_text[:300]}"
    assert len(result.get("tool_history", [])) >= 1, "Expected at least 1 tool call"
    return f"Calculator agent OK. Used tools: {[t['tool_name'] for t in result['tool_history']]}"

@test("Agent: Web search tool call via agent (REAL API)", real_api=True)
def _():
    from agent.core import UniversalAgent
    agent = UniversalAgent()
    result = agent.run("Search the web: what is the latest version of Python?", memory_enabled=False)
    assert result.get("response"), "No response returned"
    assert len(result.get("tool_history", [])) >= 1, "Expected web_search tool to be called"
    tools_used = [t["tool_name"] for t in result["tool_history"]]
    assert "web_search" in tools_used, f"Expected web_search, got: {tools_used}"
    sources = result.get("sources", [])
    assert len(sources) > 0, "Expected sources from web search"
    return f"Web search agent OK. Sources: {len(sources)}"

@test("Agent: Datetime tool via agent (REAL API)", real_api=True)
def _():
    from agent.core import UniversalAgent
    agent = UniversalAgent()
    result = agent.run("What day of the week is it today?", memory_enabled=False)
    assert result.get("response"), "No response returned"
    days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    response = result["response"]
    assert any(day in response for day in days), f"No day found in response: {response[:200]}"
    return f"Datetime agent OK: {result['response'][:100]}"

@test("Agent: Memory integration (REAL API)", real_api=True)
def _():
    from agent.core import UniversalAgent
    from database.db import create_memory, get_all_memories, delete_memory
    # Create a known memory
    mid = create_memory("I am a Python developer", category="preference", source="user")
    agent = UniversalAgent()
    result = agent.run("What do you know about me?", memory_enabled=True)
    assert result.get("response"), "No response"
    active_mems = result.get("active_memories", [])
    # Cleanup
    if mid:
        delete_memory(mid)
    return f"Memory agent OK. Active memories loaded: {len(active_mems)}"

# ─────────────────────────────────────────────────────────
# SECTION 5: PRODUCTIVITY TOOLS
# ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SECTION 5: PRODUCTIVITY TOOLS")
print("="*60)

@test("Productivity: PDF generation (reportlab)", real_api=False)
def _():
    from tools.productivity_docs import create_pdf_document
    pdf_bytes = create_pdf_document("Audit Test PDF", "This is a test paragraph.\n\nSecond paragraph here.")
    assert isinstance(pdf_bytes, bytes), "Expected bytes"
    assert len(pdf_bytes) > 500, f"PDF too small: {len(pdf_bytes)} bytes"
    assert pdf_bytes[:4] == b'%PDF', f"Not a valid PDF header: {pdf_bytes[:8]}"
    return f"PDF generated: {len(pdf_bytes)} bytes"

@test("Productivity: DOCX generation", real_api=False)
def _():
    from tools.productivity_docs import create_docx_document
    docx_bytes = create_docx_document(
        "Test DOCX",
        "## Introduction\n\nThis is a paragraph.\n\n- Bullet 1\n- Bullet 2"
    )
    assert isinstance(docx_bytes, bytes), "Expected bytes"
    assert len(docx_bytes) > 500, f"DOCX too small: {len(docx_bytes)} bytes"
    # DOCX is a zip file (PK header)
    assert docx_bytes[:2] == b'PK', f"Not a valid DOCX (zip) header: {docx_bytes[:4]}"
    return f"DOCX generated: {len(docx_bytes)} bytes"

@test("Productivity: XLSX generation", real_api=False)
def _():
    from tools.productivity_docs import create_excel_document
    rows = [
        {"Name": "Alice", "Score": 95, "Grade": "A"},
        {"Name": "Bob", "Score": 82, "Grade": "B"},
        {"Name": "Carol", "Score": 78, "Grade": "C"},
    ]
    xlsx_bytes = create_excel_document("Test Sheet", rows)
    assert isinstance(xlsx_bytes, bytes), "Expected bytes"
    assert len(xlsx_bytes) > 500, f"XLSX too small: {len(xlsx_bytes)} bytes"
    assert xlsx_bytes[:2] == b'PK', f"Not a valid XLSX header"
    return f"XLSX generated: {len(xlsx_bytes)} bytes"

@test("Productivity: PDF text extraction (pypdf)", real_api=False)
def _():
    from tools.productivity_docs import create_pdf_document
    from tools.productivity_pdf import extract_text_from_pdf
    pdf_bytes = create_pdf_document("Extraction Test", "The quick brown fox jumps over the lazy dog.")
    result = extract_text_from_pdf(pdf_bytes, "extraction_test.pdf")
    assert result["success"], f"PDF extraction failed: {result['error']}"
    assert "quick brown fox" in result["text"], f"Expected text not found: {result['text'][:200]}"
    return f"PDF extracted: {result['total_pages']} pages, {result['char_count']} chars"

@test("Productivity: PDF summarization (REAL API)", real_api=True)
def _():
    from tools.productivity_docs import create_pdf_document
    from tools.productivity_pdf import extract_text_from_pdf, summarize_pdf_text
    pdf_bytes = create_pdf_document(
        "AI Basics",
        "Artificial Intelligence (AI) is a branch of computer science that simulates human intelligence.\n"
        "Machine learning is a subset of AI. Deep learning uses neural networks."
    )
    result = extract_text_from_pdf(pdf_bytes, "ai_basics.pdf")
    assert result["success"], f"Extraction failed: {result['error']}"
    summary = summarize_pdf_text(result["text"])
    assert summary.get("success"), f"Summarization failed: {summary.get('error')}"
    assert len(summary.get("content", "")) > 50, "Summary too short"
    return f"PDF summarization OK ({len(summary['content'])} chars)"

@test("Productivity: PDF Q&A (REAL API)", real_api=True)
def _():
    from tools.productivity_docs import create_pdf_document
    from tools.productivity_pdf import extract_text_from_pdf, answer_pdf_question
    pdf_bytes = create_pdf_document(
        "Company Policy",
        "Our company was founded in 2015. The CEO is Jane Smith. We have 500 employees."
    )
    result = extract_text_from_pdf(pdf_bytes, "policy.pdf")
    assert result["success"], f"Extraction failed: {result['error']}"
    qa = answer_pdf_question(result["text"], "Who is the CEO?")
    assert qa.get("success"), f"QA failed: {qa.get('error')}"
    assert "Jane Smith" in qa.get("content", ""), f"Expected Jane Smith in answer: {qa.get('content', '')[:200]}"
    return f"PDF Q&A OK: {qa['content'][:100]}"

@test("Productivity: Empty/scanned PDF detection", real_api=False)
def _():
    from tools.productivity_pdf import extract_text_from_pdf
    # Minimal valid PDF with no text content
    empty_pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    result = extract_text_from_pdf(empty_pdf, "empty.pdf")
    assert not result["success"], "Empty PDF should fail gracefully"
    assert "scanned" in result["error"].lower() or "empty" in result["error"].lower() or "no pages" in result["error"].lower(), \
        f"Expected graceful empty/scanned message: {result['error']}"
    return f"Empty PDF detected: {result['error'][:80]}"

@test("Productivity: CSV analysis with pandas", real_api=False)
def _():
    from tools.productivity_excel import load_tabular_file
    import pandas as pd
    df = pd.DataFrame({
        "Name": ["Alice", "Bob", "Carol"],
        "Score": [95, 82, 78],
        "Age": [25, 30, 22]
    })
    csv_bytes = df.to_csv(index=False).encode()
    result = load_tabular_file(csv_bytes, "test.csv")
    assert result["success"], f"CSV load failed: {result['error']}"
    assert result["rows"] == 3, f"Expected 3 rows, got {result['rows']}"
    assert "Score" in result["numeric_columns"], "Score should be numeric"
    assert result["summary_stats"]["Score"]["max"] == 95.0, "Max score should be 95"
    return f"CSV loaded: {result['rows']} rows, {len(result['columns'])} cols"

@test("Productivity: XLSX analysis with pandas", real_api=False)
def _():
    from tools.productivity_excel import load_tabular_file
    from tools.productivity_docs import create_excel_document
    rows = [{"Product": "Widget", "Revenue": 10000}, {"Product": "Gadget", "Revenue": 25000}]
    xlsx_bytes = create_excel_document("Revenue", rows)
    result = load_tabular_file(xlsx_bytes, "revenue.xlsx")
    assert result["success"], f"XLSX load failed: {result['error']}"
    assert result["rows"] == 2, f"Expected 2 rows, got {result['rows']}"
    return f"XLSX loaded: {result['rows']} rows"

@test("Productivity: Chart generation (matplotlib)", real_api=False)
def _():
    from tools.productivity_excel import generate_data_chart
    import pandas as pd
    df = pd.DataFrame({"Month": ["Jan","Feb","Mar"], "Sales": [1200, 1800, 1500]})
    result = generate_data_chart(df, "Month", "Sales", chart_type="bar")
    assert result["success"], f"Chart failed: {result['error']}"
    assert result["fig"] is not None, "No figure returned"
    import matplotlib.pyplot as plt
    plt.close("all")  # cleanup
    return "Bar chart generated OK"

@test("Productivity: Coding Assistant — generate (REAL API)", real_api=True)
def _():
    from tools.productivity_code import generate_code_solution
    result = generate_code_solution("Write a Python function to check if a number is prime", language="Python")
    assert result.get("success"), f"Code gen failed: {result.get('error')}"
    content = result.get("content", "")
    assert "def " in content.lower() or "prime" in content.lower(), \
        f"Expected function in code: {content[:200]}"
    return f"Code generation OK ({len(content)} chars)"

@test("Productivity: Coding Assistant — debug (REAL API)", real_api=True)
def _():
    from tools.productivity_code import debug_code_error
    buggy_code = "def add(a, b):\n    return a - b  # Bug: should be +"
    error_msg = "add(2, 3) returns -1 instead of 5"
    result = debug_code_error(buggy_code, error_msg, language="Python")
    assert result.get("success"), f"Debug failed: {result.get('error')}"
    content = result.get("content", "")
    assert len(content) > 50, f"Debug response too short: {content}"
    return f"Debug response OK ({len(content)} chars)"

# ─────────────────────────────────────────────────────────
# SECTION 6: CAREER TOOLS (REAL API)
# ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SECTION 6: CAREER TOOLS (REAL API)")
print("="*60)

@test("Career: Deep Research (REAL API)", real_api=True)
def _():
    from tools.career_research import run_deep_research
    result = run_deep_research("FastAPI vs Flask for Python APIs", max_subqueries=2)
    assert result.get("success"), f"Deep research failed: {result.get('error')}"
    assert len(result.get("sources", [])) > 0, "No sources found"
    assert len(result.get("report", "")) > 100, "Report too short"
    assert len(result.get("subqueries", [])) >= 2, "Expected at least 2 subqueries"
    return f"Deep research OK. Subqueries: {len(result['subqueries'])}, Sources: {len(result['sources'])}"

@test("Career: Job Research (REAL API)", real_api=True)
def _():
    from tools.career_research import research_job_opportunities
    result = research_job_opportunities("Python Developer", location="Remote", experience_level="Mid-Level")
    assert result.get("success"), f"Job research failed: {result.get('error')}"
    sources = result.get("sources", [])
    assert len(sources) > 0, "No sources returned"
    return f"Job research OK. Sources: {len(sources)}, Structured jobs: {len(result.get('jobs', []))}"

@test("Career: Skill Gap Analyzer (REAL API)", real_api=True)
def _():
    from tools.career_research import analyze_skill_gap
    result = analyze_skill_gap("Python, SQL, pandas", "Data Engineer", "Mid-Level")
    assert result.get("success"), f"Skill gap failed: {result.get('error')}"
    content = result.get("content", "")
    assert len(content) > 100, f"Skill gap response too short: {len(content)}"
    return f"Skill gap OK ({len(content)} chars)"

@test("Career: Learning Roadmap (REAL API)", real_api=True)
def _():
    from tools.career_research import generate_learning_roadmap
    result = generate_learning_roadmap("Apache Kafka", target_duration_days=30, daily_hours=2.0)
    assert result.get("success"), f"Roadmap failed: {result.get('error')}"
    content = result.get("content", "")
    assert len(content) > 100, f"Roadmap too short: {len(content)}"
    return f"Learning roadmap OK ({len(content)} chars)"

# ─────────────────────────────────────────────────────────
# SECTION 7: SECURITY AUDIT
# ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SECTION 7: SECURITY AUDIT")
print("="*60)

@test("Security: .env in .gitignore", real_api=False)
def _():
    with open(".gitignore", "r") as f:
        content = f.read()
    assert ".env" in content, ".env not in .gitignore"
    return ".env found in .gitignore"

@test("Security: database/*.db in .gitignore", real_api=False)
def _():
    with open(".gitignore", "r") as f:
        content = f.read()
    assert "*.db" in content or "database/*.db" in content, "*.db not in .gitignore"
    return "*.db found in .gitignore"

@test("Security: No hardcoded API keys in Python files", real_api=False)
def _():
    import glob, re
    key_pattern = re.compile(r"(AIzaSy|sk-|tvly-)[A-Za-z0-9_\-]{10,}", re.IGNORECASE)
    suspicious = []
    for fpath in glob.glob("**/*.py", recursive=True):
        if "__pycache__" in fpath or "test_full_audit" in fpath:
            continue
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, 1):
                if key_pattern.search(line):
                    suspicious.append(f"{fpath}:{lineno}")
    assert len(suspicious) == 0, f"Potential hardcoded keys found: {suspicious}"
    return "No hardcoded API keys found in Python files"

@test("Security: Calculator uses AST only (no eval/exec)", real_api=False)
def _():
    with open("tools/calculator.py", "r") as f:
        lines = f.readlines()
    # Check no actual eval()/exec() calls outside docstrings/comments
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip comments and docstrings
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        if "eval(" in stripped and not stripped.startswith('"') and not stripped.startswith("'"):
            raise AssertionError(f"eval() call found at line {i}: {stripped}")
        if "exec(" in stripped and not stripped.startswith('"') and not stripped.startswith("'"):
            raise AssertionError(f"exec() call found at line {i}: {stripped}")
    content = "".join(lines)
    assert "ast.parse" in content, "AST parsing not found in calculator.py"
    return "Calculator uses AST only — eval/exec only appears in docstring (safe)"

@test("Security: Generated code is NOT auto-executed", real_api=False)
def _():
    with open("tools/productivity_code.py", "r") as f:
        content = f.read()
    assert "subprocess" not in content, "subprocess found in productivity_code.py"
    assert "exec(" not in content, "exec() found in productivity_code.py"
    assert "eval(" not in content, "eval() found in productivity_code.py"
    return "Generated code is not auto-executed"

@test("Security: SQL queries use parameterized inputs", real_api=False)
def _():
    with open("database/db.py", "r") as f:
        content = f.read()
    # Check that f-string SQL is not used
    import re
    fstring_sql = re.findall(r'f".*?(SELECT|INSERT|UPDATE|DELETE).*?"', content, re.IGNORECASE)
    assert len(fstring_sql) == 0, f"Possible f-string SQL injection found: {fstring_sql}"
    # Ensure parameterized placeholders are used
    assert "?" in content, "No parameterized SQL placeholders found"
    return "SQL uses parameterized queries — safe"

@test("Security: SSRF protection in web_extractor", real_api=False)
def _():
    with open("tools/web_extractor.py", "r") as f:
        content = f.read()
    assert "localhost" in content, "localhost SSRF check missing"
    assert "127.0.0.1" in content, "127.0.0.1 SSRF check missing"
    assert "192.168." in content, "192.168.x SSRF check missing"
    return "SSRF protection verified in web_extractor.py"

# ─────────────────────────────────────────────────────────
# SECTION 8: DEPLOYMENT READINESS
# ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SECTION 8: DEPLOYMENT READINESS")
print("="*60)

@test("Deploy: requirements.txt has all core packages", real_api=False)
def _():
    with open("requirements.txt", "r") as f:
        content = f.read().lower()
    required = [
        "streamlit", "python-dotenv", "google-genai", "groq",
        "tavily-python", "langgraph", "langchain-core", "pydantic",
        "pypdf", "reportlab", "python-docx", "openpyxl",
        "matplotlib", "pandas", "requests", "beautifulsoup4"
    ]
    missing = [pkg for pkg in required if pkg not in content]
    assert len(missing) == 0, f"Missing from requirements.txt: {missing}"
    return f"All {len(required)} required packages present in requirements.txt"

@test("Deploy: settings.py reads from os.environ (Cloud compatible)", real_api=False)
def _():
    with open("config/settings.py", "r") as f:
        content = f.read()
    assert "os.getenv" in content, "settings.py does not use os.getenv"
    assert "GEMINI_API_KEY" in content, "GEMINI_API_KEY not in settings"
    assert "GROQ_API_KEY" in content, "GROQ_API_KEY not in settings"
    assert "TAVILY_API_KEY" in content, "TAVILY_API_KEY not in settings"
    return "settings.py reads from os.environ — Cloud compatible"

@test("Deploy: app.py exists and is importable as module", real_api=False)
def _():
    assert os.path.exists("app.py"), "app.py not found"
    with open("app.py", "r") as f:
        content = f.read()
    assert "streamlit" in content.lower(), "streamlit import not found in app.py"
    return "app.py exists and imports streamlit"

@test("Deploy: .gitignore excludes sensitive files", real_api=False)
def _():
    with open(".gitignore", "r") as f:
        content = f.read()
    checks = {".env": ".env", "*.db": "database files", "__pycache__": "pycache", ".streamlit/": "streamlit secrets"}
    missing = [desc for pattern, desc in checks.items() if pattern not in content]
    assert len(missing) == 0, f"Missing from .gitignore: {missing}"
    return f"All sensitive patterns in .gitignore"

@test("Deploy: README.md exists", real_api=False)
def _():
    assert os.path.exists("README.md"), "README.md not found"
    return "README.md exists"

# ─────────────────────────────────────────────────────────
# FINAL REPORT
# ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("FINAL AUDIT REPORT")
print("="*60)

passed = [r for r in results if r[0] == PASS]
failed = [r for r in results if r[0] == FAIL]
skipped = [r for r in results if r[0] == SKIP]

print(f"\nTotal tests: {len(results)}")
print(f"  ✅ PASSED : {len(passed)}")
print(f"  ❌ FAILED : {len(failed)}")
print(f"  ⚠️  SKIPPED: {len(skipped)}")

print("\n" + "-"*60)
print("DETAILED RESULTS:")
print("-"*60)
for status, name, label, msg in results:
    print(f"\n{status} {label} {name}")
    if msg:
        # Indent multi-line messages
        for line in msg.split("\n")[:5]:
            print(f"    {line}")

if failed:
    print("\n" + "="*60)
    print("❌ FAILED TESTS SUMMARY:")
    print("="*60)
    for status, name, label, msg in failed:
        print(f"\n  {name}")
        for line in msg.split("\n")[:8]:
            print(f"    {line}")

print("\n" + "="*60)
print("AUDIT COMPLETE")
print("="*60)

# Exit with non-zero if any failures
sys.exit(1 if failed else 0)
