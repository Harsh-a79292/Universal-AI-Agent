"""
Comprehensive Multi-User Authentication and Data Isolation Test Suite
Tests:
- User registration with bcrypt hashing (automatic salt verification).
- Password validation and duplicate registration prevention.
- Brute-force rate limiting on failed logins.
- Alice and Bob registration and login.
- Alice creates a chat session, chat message, note, memory, reminder, and career plan.
- Bob must see 0 of Alice's records across all tables.
- Bob cannot modify or delete Alice's records even when given Alice's record IDs.
- Alice can still access, update, and manage all her own records.
- Agent memory scoping: Alice's facts are never retrieved in Bob's context.
- Database migrations preserve existing data.
"""
import sys
import os
import uuid
import sqlite3
import bcrypt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import (
    init_db,
    register_user,
    authenticate_user,
    create_session,
    get_all_sessions,
    update_session_title,
    toggle_pin_session,
    delete_session,
    save_message,
    get_session_messages,
    create_note,
    get_all_notes,
    update_note,
    delete_note,
    create_memory,
    get_all_memories,
    update_memory,
    delete_memory,
    create_reminder,
    get_all_reminders,
    get_due_reminders,
    update_reminder,
    set_reminder_completed,
    delete_reminder,
    create_career_plan,
    get_all_career_plans,
    update_career_plan_tasks,
    delete_career_plan
)
from agent.core import UniversalAgent
from config.settings import settings

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def run_test(name, fn):
    try:
        msg = fn()
        results.append((PASS, name, msg or ""))
    except Exception as e:
        results.append((FAIL, name, str(e)))

print("\n" + "="*60)
print("MULTI-USER AUTHENTICATION & DATA ISOLATION TEST SUITE")
print("="*60)

# Initialize and verify schema migration
init_db()

# 1. Registration & bcrypt password hashing
alice_name = f"alice_{uuid.uuid4().hex[:6]}"
bob_name = f"bob_{uuid.uuid4().hex[:6]}"
alice_pw = "AliceSecurePass123!"
bob_pw = "BobSecurePass456!"

alice_id = None
bob_id = None

def test_registration_and_hashing():
    global alice_id, bob_id
    success, msg, uid = register_user(alice_name, alice_pw)
    assert success, f"Alice registration failed: {msg}"
    assert isinstance(uid, int) and uid > 0
    alice_id = uid

    # Verify password in DB is bcrypt hash, NOT plaintext
    with sqlite3.connect(settings.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (alice_id,))
        row = cursor.fetchone()
        assert row, "Alice not found in users table"
        stored_hash = row[0]
        assert alice_pw not in stored_hash, "Plaintext password stored in database!"
        assert stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"), "Not a valid bcrypt hash"

    # Register Bob
    success_b, msg_b, uid_b = register_user(bob_name, bob_pw)
    assert success_b, f"Bob registration failed: {msg_b}"
    bob_id = uid_b

    return f"Alice (id={alice_id}) & Bob (id={bob_id}) registered with salted bcrypt hashes."
run_test("Auth: Registration with salted bcrypt hashing", test_registration_and_hashing)

# 2. Duplicate registration prevention
def test_duplicate_registration():
    success, msg, uid = register_user(alice_name, "AnotherPassword123")
    assert not success, "Duplicate registration should fail"
    assert "already exists" in msg.lower(), f"Unexpected error message: {msg}"
    return f"Duplicate username rejected: {msg}"
run_test("Auth: Duplicate registration blocked", test_duplicate_registration)

# 3. Invalid credentials and login rate limiting
def test_login_and_rate_limiting():
    # Invalid password
    succ, msg, u = authenticate_user(alice_name, "WrongPassword")
    assert not succ, "Invalid password should fail"
    assert "invalid" in msg.lower()

    # Successful login
    succ_ok, msg_ok, u_ok = authenticate_user(alice_name, alice_pw)
    assert succ_ok and u_ok["id"] == alice_id, f"Valid login failed: {msg_ok}"

    # Rate limiting test: 5 wrong attempts trigger lockout
    brute_user = f"attacker_{uuid.uuid4().hex[:6]}"
    register_user(brute_user, "GoodPassword123")
    for _ in range(5):
        authenticate_user(brute_user, "BadPass")
    locked, lock_msg, _ = authenticate_user(brute_user, "GoodPassword123")
    assert not locked, "Attacker should be locked out after 5 failed attempts"
    assert "too many failed" in lock_msg.lower(), f"Expected lockout message, got: {lock_msg}"
    return "Password verification and brute-force lockout verified."
run_test("Auth: Password verification & brute-force lockout", test_login_and_rate_limiting)

# 4. Chat session isolation: Alice creates a session, Bob sees 0
alice_session_id = f"alice-session-{uuid.uuid4()}"

def test_session_isolation():
    create_session(alice_session_id, "Alice Secret Project", user_id=alice_id)
    save_message(alice_session_id, "user", "Alice's proprietary secret code 999", user_id=alice_id)
    save_message(alice_session_id, "assistant", "Confirmed secret acknowledged.", user_id=alice_id)

    # Alice queries sessions
    alice_sessions = get_all_sessions(user_id=alice_id)
    assert any(s["id"] == alice_session_id for s in alice_sessions), "Alice cannot see her own session"

    # Bob queries sessions
    bob_sessions = get_all_sessions(user_id=bob_id)
    assert not any(s["id"] == alice_session_id for s in bob_sessions), "LEAK: Bob can see Alice's session!"

    # Bob queries messages of Alice's session
    bob_msgs = get_session_messages(alice_session_id, user_id=bob_id)
    assert len(bob_msgs) == 0, f"LEAK: Bob retrieved Alice's messages: {bob_msgs}"

    # Bob attempts to rename Alice's session
    renamed = update_session_title(alice_session_id, "Hacked by Bob", user_id=bob_id)
    assert not renamed, "TAMPER: Bob was able to rename Alice's session!"

    # Verify title remains unchanged
    with sqlite3.connect(settings.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM sessions WHERE id = ?", (alice_session_id,))
        assert cursor.fetchone()[0] == "Alice Secret Project"

    # Bob attempts to delete Alice's session
    deleted = delete_session(alice_session_id, user_id=bob_id)
    assert not deleted, "TAMPER: Bob was able to delete Alice's session!"

    return "Chat sessions and messages strictly isolated between Alice and Bob."
run_test("Isolation: Chat sessions & messages", test_session_isolation)

# 5. Smart Notes isolation
alice_note_id = None

def test_notes_isolation():
    global alice_note_id
    alice_note_id = create_note("Alice Private Diary", "Top secret note content", tags="confidential", user_id=alice_id)
    assert isinstance(alice_note_id, int) and alice_note_id > 0

    # Bob lists notes
    bob_notes = get_all_notes(user_id=bob_id)
    assert not any(n["id"] == alice_note_id for n in bob_notes), "LEAK: Bob can see Alice's note!"

    # Bob searches notes
    bob_search = get_all_notes(user_id=bob_id, search_query="Top secret")
    assert len(bob_search) == 0, "LEAK: Bob's search leaked Alice's note!"

    # Bob attempts to edit Alice's note
    updated = update_note(alice_note_id, "Hacked Note", "Defaced", user_id=bob_id)
    assert not updated, "TAMPER: Bob was able to edit Alice's note!"

    # Bob attempts to delete Alice's note
    deleted = delete_note(alice_note_id, user_id=bob_id)
    assert not deleted, "TAMPER: Bob was able to delete Alice's note!"

    # Alice can view and edit her note
    alice_notes = get_all_notes(user_id=alice_id)
    assert any(n["id"] == alice_note_id for n in alice_notes), "Alice cannot see her note"
    return "Smart Notes strictly isolated between Alice and Bob."
run_test("Isolation: Smart Notes", test_notes_isolation)

# 6. Long-term Memory isolation
alice_mem_id = None

def test_memory_isolation():
    global alice_mem_id
    alice_mem_id = create_memory("Alice prefers Dark Chocolate", category="diet", user_id=alice_id)

    # Bob lists memories
    bob_mems = get_all_memories(user_id=bob_id)
    assert not any(m["content"] == "Alice prefers Dark Chocolate" for m in bob_mems), "LEAK: Bob can see Alice's memory!"

    # Bob attempts to edit Alice's memory
    updated = update_memory(alice_mem_id, "Alice prefers Milk Chocolate", user_id=bob_id)
    assert not updated, "TAMPER: Bob was able to edit Alice's memory!"

    # Bob attempts to delete Alice's memory
    deleted = delete_memory(alice_mem_id, user_id=bob_id)
    assert not deleted, "TAMPER: Bob was able to delete Alice's memory!"

    # Alice can see her memory
    alice_mems = get_all_memories(user_id=alice_id)
    assert any(m["id"] == alice_mem_id for m in alice_mems), "Alice cannot see her memory"
    return "Long-term memories strictly isolated between Alice and Bob."
run_test("Isolation: Long-term Memories", test_memory_isolation)

# 7. Reminders isolation
alice_rem_id = None

def test_reminders_isolation():
    global alice_rem_id
    from datetime import datetime, timedelta
    past = (datetime.now() - timedelta(minutes=5)).isoformat()
    alice_rem_id = create_reminder("Alice Doctor Appointment", due_datetime=past, description="Confidential health", user_id=alice_id)

    # Bob checks reminders
    bob_rems = get_all_reminders(user_id=bob_id)
    assert not any(r["id"] == alice_rem_id for r in bob_rems), "LEAK: Bob can see Alice's reminder!"

    # Bob checks due reminders
    bob_due = get_due_reminders(user_id=bob_id)
    assert not any(r["id"] == alice_rem_id for r in bob_due), "LEAK: Bob received Alice's due reminder alert!"

    # Bob attempts to complete or delete Alice's reminder
    comp = set_reminder_completed(alice_rem_id, True, user_id=bob_id)
    assert not comp, "TAMPER: Bob was able to complete Alice's reminder!"

    del_rem = delete_reminder(alice_rem_id, user_id=bob_id)
    assert not del_rem, "TAMPER: Bob was able to delete Alice's reminder!"

    # Alice checks her reminders
    alice_due = get_due_reminders(user_id=alice_id)
    assert any(r["id"] == alice_rem_id for r in alice_due), "Alice cannot see her due reminder"
    return "Reminders strictly isolated between Alice and Bob."
run_test("Isolation: Reminders", test_reminders_isolation)

# 8. Career Plans isolation
alice_plan_id = None

def test_career_plans_isolation():
    global alice_plan_id
    tasks = [{"title": "Alice Task 1", "completed": False}, {"title": "Alice Task 2", "completed": True}]
    alice_plan_id = create_career_plan("Alice VP of Engineering", tasks, total_days=90, user_id=alice_id)

    # Bob checks career plans
    bob_plans = get_all_career_plans(user_id=bob_id)
    assert not any(p["id"] == alice_plan_id for p in bob_plans), "LEAK: Bob can see Alice's career plan!"

    # Bob attempts to update tasks
    upd = update_career_plan_tasks(alice_plan_id, [{"title": "Hacked", "completed": True}], user_id=bob_id)
    assert not upd, "TAMPER: Bob was able to modify Alice's career plan tasks!"

    # Bob attempts to delete Alice's career plan
    d_plan = delete_career_plan(alice_plan_id, user_id=bob_id)
    assert not d_plan, "TAMPER: Bob was able to delete Alice's career plan!"

    # Alice sees her plan with 50% progress
    alice_plans = get_all_career_plans(user_id=alice_id)
    p = next((x for x in alice_plans if x["id"] == alice_plan_id), None)
    assert p and abs(p["progress_pct"] - 50.0) < 0.01
    return "Career plans strictly isolated between Alice and Bob."
run_test("Isolation: Career Plans", test_career_plans_isolation)

# 9. Agent Context Scoping: Alice's memory is NOT loaded into Bob's agent
def test_agent_memory_scoping():
    agent = UniversalAgent()
    # Mock LLM generation to inspect memory context passed into query_llm_with_fallback
    from unittest.mock import patch
    captured_prompts = []

    def mock_llm_fallback(prompt, system_instruction, preferred_model="auto"):
        captured_prompts.append(prompt)
        return {"success": True, "content": "I understand your request.", "model": "MockedLLM"}

    with patch("models.llm_service.query_llm_with_fallback", side_effect=mock_llm_fallback):
        # Bob asks a question
        agent.run("What do you know about my dietary preferences?", memory_enabled=True, user_id=bob_id)

    # Verify Alice's memory ("Alice prefers Dark Chocolate") never appeared in Bob's prompt context
    for prompt in captured_prompts:
        assert "Alice prefers Dark Chocolate" not in prompt, "LEAK: Alice's memory leaked into Bob's agent context!"
    return "Agent ReAct memory retrieval strictly scoped to authenticated user."
run_test("Agent: Memory scoping strictly by user_id", test_agent_memory_scoping)

# 10. Database Migration Data Preservation
def test_database_migration_preservation():
    # Insert legacy record under user_id 1
    create_note("Legacy Note Before Migration", "Historical data", user_id=1)
    # Re-run init_db() to simulate server restart / repeated migration
    init_db()
    legacy_notes = get_all_notes(user_id=1)
    assert any(n["title"] == "Legacy Note Before Migration" for n in legacy_notes), "Migration wiped legacy data!"
    # Bob (user_id > 1) cannot see user 1's legacy notes
    bob_notes = get_all_notes(user_id=bob_id)
    assert not any(n["title"] == "Legacy Note Before Migration" for n in bob_notes), "Legacy data exposed to new user!"
    return "Safe repeatable migrations preserve data without exposing it to new users."
run_test("DB: Migration repeatability and data preservation", test_database_migration_preservation)

print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
passed = [r for r in results if r[0] == PASS]
failed = [r for r in results if r[0] == FAIL]
print(f"Total: {len(results)}   PASS: {len(passed)}   FAIL: {len(failed)}")
print("="*60)

for status, name, msg in results:
    print(f"{status}  {name}")
    if msg:
        print(f"      {msg[:100]}")

if failed:
    print("\nFAILED TESTS:")
    for _, name, msg in failed:
        print(f"FAIL: {name} -> {msg}")
    sys.exit(1)

print("\nALL MULTI-USER AUTH & ISOLATION TESTS PASSED (10/10)!")

