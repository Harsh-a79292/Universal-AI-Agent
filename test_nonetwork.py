"""Non-network test suite — runs in sandbox safely."""
import sys, os, io, json, uuid, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "PASS"; FAIL = "FAIL"
results = []

def run_test(name, fn):
    try:
        msg = fn()
        results.append((PASS, name, msg or ""))
    except Exception as e:
        results.append((FAIL, name, f"{type(e).__name__}: {e}"))

def test_db_session():
    from database.db import init_db, create_session, get_all_sessions
    init_db()
    sid = f"test-{uuid.uuid4()}"
    create_session(sid, "Test Session")
    sessions = get_all_sessions()
    assert any(s["id"] == sid for s in sessions)
    return "Session CRUD OK"
run_test("DB: create_session + get_all_sessions", test_db_session)

def test_db_save_message():
    from database.db import create_session, save_message, get_session_messages
    sid = f"test-msg-{uuid.uuid4()}"
    create_session(sid, "Msg Test")
    activities = [{"stage": "planning", "message": "Test plan"}]
    tool_history = [{"tool_name": "calc", "tool_args": {}, "result_summary": "4"}]
    save_message(session_id=sid, role="assistant", content="Test", model_used="gemini",
                 activities=activities, tool_history=tool_history)
    msgs = get_session_messages(sid)
    assert len(msgs) == 1
    assert msgs[0]["activities"] == activities
    assert msgs[0]["tool_history"] == tool_history
    return "save_message with all fields OK"
run_test("DB: save_message with activities+tool_history", test_db_save_message)

def test_career_plan():
    from database.db import create_career_plan, get_all_career_plans, update_career_plan_tasks, delete_career_plan
    tasks = [{"title": "T1", "completed": False}, {"title": "T2", "completed": True}]
    pid = create_career_plan("Test Goal", tasks, 90)
    plans = get_all_career_plans()
    p = next(x for x in plans if x["id"] == pid)
    assert p["total_tasks"] == 2 and p["completed_tasks"] == 1
    assert abs(p["progress_pct"] - 50.0) < 0.01, f"Expected 50%, got {p['progress_pct']}"
    update_career_plan_tasks(pid, [{"title": "T1", "completed": True}, {"title": "T2", "completed": True}])
    plans2 = get_all_career_plans()
    p2 = next(x for x in plans2 if x["id"] == pid)
    assert abs(p2["progress_pct"] - 100.0) < 0.01
    delete_career_plan(pid)
    plans3 = get_all_career_plans()
    assert not any(x["id"] == pid for x in plans3)
    return "Career plan CRUD + 50%/100% progress OK"
run_test("DB: Career plan CRUD + progress tracking", test_career_plan)

def test_notes():
    from database.db import create_note, update_note, get_all_notes, delete_note
    nid = create_note("Test Note", "Test content", tags="audit")
    assert isinstance(nid, int) and nid > 0
    update_note(nid, "Updated Title", "Updated content", tags="updated")
    notes = get_all_notes(search_query="Updated")
    assert any(n["id"] == nid for n in notes)
    delete_note(nid)
    assert not any(n["id"] == nid for n in get_all_notes())
    return "Notes CRUD OK"
run_test("DB: Smart Notes CRUD", test_notes)

def test_memory():
    from database.db import create_memory, get_all_memories, update_memory, delete_memory
    mid = create_memory("I prefer Python", category="preference", source="user")
    mems = get_all_memories()
    target = next((m for m in mems if m["content"] == "I prefer Python"), None)
    assert target, "Memory not found"
    update_memory(target["id"], "I prefer Python 3", category="language", is_enabled=True)
    mems2 = get_all_memories()
    t2 = next((m for m in mems2 if m["id"] == target["id"]), None)
    assert t2 and t2["content"] == "I prefer Python 3"
    delete_memory(target["id"])
    assert not any(m["id"] == target["id"] for m in get_all_memories())
    return "Memory CRUD OK"
run_test("DB: Long-term Memory CRUD", test_memory)

def test_reminders():
    from database.db import create_reminder, get_all_reminders, get_due_reminders, mark_reminder_notified, set_reminder_completed, delete_reminder
    from datetime import datetime, timedelta
    past = (datetime.now() - timedelta(minutes=5)).isoformat()
    rid = create_reminder("Audit Reminder", due_datetime=past, description="Test")
    due = get_due_reminders()
    assert any(r["id"] == rid for r in due)
    mark_reminder_notified(rid)
    assert not any(r["id"] == rid for r in get_due_reminders())
    set_reminder_completed(rid, True)
    all_r = get_all_reminders()
    target = next((r for r in all_r if r["id"] == rid), None)
    assert target and target["is_completed"] == 1
    delete_reminder(rid)
    assert not any(r["id"] == rid for r in get_all_reminders())
    return "Reminder lifecycle OK"
run_test("DB: Reminders lifecycle", test_reminders)

def test_chat_mgmt():
    from database.db import create_session, get_all_sessions, toggle_pin_session, update_session_title, delete_session, save_message
    sid = f"test-search-{uuid.uuid4()}"
    create_session(sid, "SearchableSession")
    save_message(sid, "user", "unique content xyz987")
    assert any(s["id"] == sid for s in get_all_sessions(search_query="SearchableSession"))
    assert any(s["id"] == sid for s in get_all_sessions(search_query="unique content xyz987"))
    toggle_pin_session(sid, True)
    sessions = get_all_sessions()
    target = next(s for s in sessions if s["id"] == sid)
    assert target["is_pinned"] == 1
    update_session_title(sid, "RenamedSession")
    renamed = next(s for s in get_all_sessions() if s["id"] == sid)
    assert renamed["title"] == "RenamedSession"
    delete_session(sid)
    assert not any(s["id"] == sid for s in get_all_sessions())
    return "Chat search + pin + rename + delete OK"
run_test("DB: Chat management (search/pin/rename/delete)", test_chat_mgmt)

def test_calculator():
    from tools.calculator import calculate_expression
    r = calculate_expression("sqrt(144) + 7 * 3")
    assert r["success"] and abs(r["result"] - 33.0) < 0.001
    r2 = calculate_expression("10/0")
    assert not r2["success"] and "zero" in r2["error"].lower()
    r3 = calculate_expression("2 ** 3 + pi")
    assert r3["success"] and abs(r3["result"] - (8 + 3.14159265)) < 0.0001
    return f"Calculator OK. sqrt(144)+7*3={r['result']}, 2**3+pi={r3['result']:.4f}"
run_test("Tool: Calculator (arithmetic + functions + constants)", test_calculator)

def test_calculator_injection():
    from tools.calculator import calculate_expression
    r = calculate_expression("__import__('os').system('echo hack')")
    assert not r["success"], "Should block unsafe expressions"
    return f"Code injection blocked: {r['error'][:60]}"
run_test("Tool: Calculator — code injection blocked", test_calculator_injection)

def test_datetime():
    from tools.datetime_tool import get_current_datetime
    r = get_current_datetime()
    assert r["success"] and r.get("date") and r.get("day_of_week")
    r2 = get_current_datetime(timezone_name="Asia/Kolkata")
    assert r2["success"]
    return f"DateTime OK: {r['formatted']}"
run_test("Tool: Datetime (local + IST timezone)", test_datetime)

def test_ssrf():
    from tools.web_extractor import extract_website_content
    r1 = extract_website_content("http://localhost:8080")
    assert not r1["success"] and ("safety" in r1["error"].lower() or "blocked" in r1["error"].lower())
    r2 = extract_website_content("http://192.168.1.1")
    assert not r2["success"]
    r3 = extract_website_content("ftp://example.com")
    assert not r3["success"]
    return "SSRF + scheme validation OK"
run_test("Tool: Web extractor — SSRF + invalid scheme blocked", test_ssrf)

def test_pdf_gen():
    from tools.productivity_docs import create_pdf_document
    b = create_pdf_document("Test PDF", "First paragraph.\n\nSecond paragraph.")
    assert isinstance(b, bytes) and len(b) > 500 and b[:4] == b"%PDF"
    return f"PDF generated: {len(b)} bytes"
run_test("Productivity: PDF generation (reportlab)", test_pdf_gen)

def test_docx_gen():
    from tools.productivity_docs import create_docx_document
    b = create_docx_document("Test DOCX", "## Section\n\nBody text.\n\n- Item 1\n- Item 2")
    assert isinstance(b, bytes) and len(b) > 500 and b[:2] == b"PK"
    return f"DOCX generated: {len(b)} bytes"
run_test("Productivity: DOCX generation (python-docx)", test_docx_gen)

def test_xlsx_gen():
    from tools.productivity_docs import create_excel_document
    rows = [{"Name": "Alice", "Score": 95}, {"Name": "Bob", "Score": 82}]
    b = create_excel_document("Sheet", rows)
    assert isinstance(b, bytes) and len(b) > 500 and b[:2] == b"PK"
    return f"XLSX generated: {len(b)} bytes"
run_test("Productivity: XLSX generation (openpyxl)", test_xlsx_gen)

def test_pdf_extract():
    from tools.productivity_docs import create_pdf_document
    from tools.productivity_pdf import extract_text_from_pdf
    pdf_b = create_pdf_document("Extraction Test", "The quick brown fox jumps over the lazy dog.")
    r = extract_text_from_pdf(pdf_b, "test.pdf")
    assert r["success"] and "quick brown fox" in r["text"]
    return f"PDF extracted: {r['total_pages']} pages, {r['char_count']} chars"
run_test("Productivity: PDF text extraction (pypdf)", test_pdf_extract)

def test_scanned_pdf():
    from tools.productivity_pdf import extract_text_from_pdf
    empty_pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    r = extract_text_from_pdf(empty_pdf, "empty.pdf")
    assert not r["success"], "Empty PDF should fail gracefully"
    err = r["error"].lower()
    assert "scanned" in err or "empty" in err or "no pages" in err or "page" in err
    return f"Empty/scanned PDF detected gracefully: {r['error'][:60]}"
run_test("Productivity: Empty/scanned PDF detection", test_scanned_pdf)

def test_csv_analysis():
    import pandas as pd
    from tools.productivity_excel import load_tabular_file, generate_data_chart
    df = pd.DataFrame({"Name": ["A","B","C"], "Score": [95,82,78], "Age": [25,30,22]})
    csv_b = df.to_csv(index=False).encode()
    r = load_tabular_file(csv_b, "test.csv")
    assert r["success"] and r["rows"] == 3 and "Score" in r["numeric_columns"]
    assert r["summary_stats"]["Score"]["max"] == 95.0
    return f"CSV loaded: {r['rows']} rows, {len(r['columns'])} cols"
run_test("Productivity: CSV analysis (pandas)", test_csv_analysis)

def test_chart():
    import pandas as pd
    from tools.productivity_excel import generate_data_chart
    df = pd.DataFrame({"Month": ["Jan","Feb","Mar"], "Sales": [1200,1800,1500]})
    for ctype in ["bar", "line", "scatter"]:
        r = generate_data_chart(df, "Month", "Sales", ctype)
        assert r["success"] and r["fig"] is not None, f"Chart type {ctype} failed: {r.get('error')}"
    import matplotlib.pyplot as plt; plt.close("all")
    return "Bar, line, scatter charts all OK"
run_test("Productivity: Chart generation — bar/line/scatter", test_chart)

def test_security_gitignore():
    gi = open(".gitignore").read()
    assert ".env" in gi
    assert "*.db" in gi or "database/*.db" in gi
    assert "__pycache__" in gi
    assert ".streamlit" in gi
    return ".env, *.db, __pycache__, .streamlit all ignored"
run_test("Security: .gitignore covers sensitive files", test_security_gitignore)

def test_no_hardcoded_keys():
    import glob, re
    pat = re.compile(r"(AIzaSy|sk-|tvly-)[A-Za-z0-9_\-]{10,}", re.I)
    for fp in glob.glob("**/*.py", recursive=True):
        if "__pycache__" in fp or "test_" in fp: continue
        for line in open(fp, encoding="utf-8", errors="ignore"):
            assert not pat.search(line), f"Potential key in {fp}: {line[:60]}"
    return "No hardcoded API keys in Python files"
run_test("Security: No hardcoded API keys in source", test_no_hardcoded_keys)

def test_calc_no_eval():
    import ast
    with open("tools/calculator.py", "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    dangerous_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                dangerous_calls.append(f"Line {node.lineno}: {node.func.id}()")
    assert len(dangerous_calls) == 0, f"Dangerous function calls found: {dangerous_calls}"
    assert "ast.parse" in source, "ast.parse not found in calculator source"
    return "Calculator: Verified AST-only parsing without dangerous eval() or exec() calls"
run_test("Security: Calculator uses AST only (no eval/exec calls)", test_calc_no_eval)

def test_code_not_executed():
    c = open("tools/productivity_code.py").read()
    assert "subprocess" not in c and "exec(" not in c and "eval(" not in c
    return "Generated code is NOT auto-executed"
run_test("Security: Generated code not auto-executed", test_code_not_executed)

def test_sql_parameterized():
    import re
    db_c = open("database/db.py").read()
    # Look for f-string SQL (dangerous pattern)
    fstring_sql = re.findall(r'f"[^"]*?(SELECT|INSERT|UPDATE|DELETE)[^"]*?"', db_c, re.I)
    assert len(fstring_sql) == 0, f"f-string SQL found: {fstring_sql}"
    assert "?" in db_c  # parameterized placeholders present
    return "SQL uses parameterized queries — injection-safe"
run_test("Security: SQL uses parameterized queries", test_sql_parameterized)

def test_ssrf_code():
    c = open("tools/web_extractor.py").read()
    assert "localhost" in c and "127.0.0.1" in c and "192.168." in c
    return "SSRF protection verified in source"
run_test("Security: SSRF protection in web_extractor code", test_ssrf_code)

def test_deploy_requirements():
    req = open("requirements.txt").read().lower()
    required = ["streamlit","google-genai","groq","tavily-python","langgraph","langchain-core",
                "pypdf","reportlab","python-docx","openpyxl","matplotlib","pandas","requests","beautifulsoup4"]
    missing = [p for p in required if p not in req]
    assert len(missing) == 0, f"Missing: {missing}"
    return f"All {len(required)} required packages in requirements.txt"
run_test("Deploy: requirements.txt completeness", test_deploy_requirements)

def test_deploy_settings():
    c = open("config/settings.py").read()
    assert "os.getenv" in c and "GEMINI_API_KEY" in c and "GROQ_API_KEY" in c and "TAVILY_API_KEY" in c
    return "settings.py uses os.getenv (Streamlit Cloud compatible)"
run_test("Deploy: settings.py Cloud-compatible", test_deploy_settings)

def test_deploy_entrypoint():
    assert os.path.exists("app.py") and os.path.exists("README.md")
    with open("app.py", "r", encoding="utf-8") as f:
        app_c = f.read()
    assert "streamlit" in app_c.lower() and "set_page_config" in app_c
    return "app.py entry point OK (utf-8 verified)"
run_test("Deploy: app.py entry point", test_deploy_entrypoint)

# ---- Report ----
passed = [r for r in results if r[0] == PASS]
failed = [r for r in results if r[0] == FAIL]
print(f"\n{'='*60}")
print(f"NON-NETWORK AUDIT TEST RESULTS")
print(f"{'='*60}")
print(f"Total: {len(results)}   PASS: {len(passed)}   FAIL: {len(failed)}")
print(f"{'='*60}")
for status, name, msg in results:
    icon = "✅" if status == PASS else "❌"
    print(f"{icon}  {name}")
    if msg: print(f"      {msg[:120]}")

if failed:
    print(f"\n{'='*60}")
    print("FAILED TESTS:")
    print(f"{'='*60}")
    for _, name, msg in failed:
        print(f"\n❌ {name}")
        print(f"   {msg[:300]}")

sys.exit(1 if failed else 0)

