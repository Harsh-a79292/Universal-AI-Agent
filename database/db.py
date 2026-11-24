import sqlite3
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import bcrypt
from config.settings import settings

# In-memory rate limiting dictionary: {username: [timestamps]}
_LOGIN_ATTEMPTS: Dict[str, List[float]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 300  # 5 minutes lockout

def init_db():
    """
    Initialize SQLite database tables for users, sessions, messages, notes, memories, reminders, career_plans.
    Includes safe table-rebuilding migrations ensuring strict multi-tenant isolation.
    """
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")

        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Check and migrate legacy / default user for existing single-user data
        cursor.execute("SELECT id FROM users WHERE id = 1")
        if not cursor.fetchone():
            legacy_dummy_hash = bcrypt.hashpw(b"legacy_admin_placeholder_secure_pw", bcrypt.gensalt(rounds=12)).decode("utf-8")
            cursor.execute(
                "INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (1, 'legacy_default_user', ?)",
                (legacy_dummy_hash,)
            )

        # 3. Sessions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL DEFAULT 1,
                title TEXT NOT NULL,
                is_pinned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # 4. Messages Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER NOT NULL DEFAULT 1,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model_used TEXT,
                sources TEXT,
                agent_logs TEXT,
                activities TEXT,
                tool_history TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # 5. Notes Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                session_id TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # 6. Memories Table (Scoped uniquely per user_id, content)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                category TEXT DEFAULT 'general',
                content TEXT NOT NULL,
                source TEXT DEFAULT 'user',
                is_enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE (user_id, content)
            )
        """)

        # 7. Reminders Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                title TEXT NOT NULL,
                description TEXT,
                due_datetime TEXT NOT NULL,
                is_completed INTEGER DEFAULT 0,
                is_notified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # 8. Career Plans Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS career_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                goal_title TEXT NOT NULL,
                total_days INTEGER DEFAULT 90,
                tasks_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # ---------------- SAFE MIGRATIONS FOR EXISTING SCHEMAS ----------------
        # A. sessions.user_id & sessions.is_pinned
        cursor.execute("PRAGMA table_info(sessions)")
        cols = [c[1] for c in cursor.fetchall()]
        if "user_id" not in cols:
            cursor.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
        if "is_pinned" not in cols:
            cursor.execute("ALTER TABLE sessions ADD COLUMN is_pinned INTEGER DEFAULT 0")

        # B. messages.user_id, activities, tool_history
        cursor.execute("PRAGMA table_info(messages)")
        cols = [c[1] for c in cursor.fetchall()]
        if "user_id" not in cols:
            cursor.execute("ALTER TABLE messages ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
        if "activities" not in cols:
            cursor.execute("ALTER TABLE messages ADD COLUMN activities TEXT")
        if "tool_history" not in cols:
            cursor.execute("ALTER TABLE messages ADD COLUMN tool_history TEXT")

        # C. notes.user_id
        cursor.execute("PRAGMA table_info(notes)")
        cols = [c[1] for c in cursor.fetchall()]
        if "user_id" not in cols:
            cursor.execute("ALTER TABLE notes ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")

        # D. reminders.user_id
        cursor.execute("PRAGMA table_info(reminders)")
        cols = [c[1] for c in cursor.fetchall()]
        if "user_id" not in cols:
            cursor.execute("ALTER TABLE reminders ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")

        # E. career_plans.user_id
        cursor.execute("PRAGMA table_info(career_plans)")
        cols = [c[1] for c in cursor.fetchall()]
        if "user_id" not in cols:
            cursor.execute("ALTER TABLE career_plans ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")

        # F. memories: Safe table rebuilding to change global UNIQUE(content) -> composite UNIQUE(user_id, content)
        cursor.execute("PRAGMA table_info(memories)")
        m_cols = [c[1] for c in cursor.fetchall()]
        if "user_id" not in m_cols:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    category TEXT DEFAULT 'general',
                    content TEXT NOT NULL,
                    source TEXT DEFAULT 'user',
                    is_enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    UNIQUE (user_id, content)
                )
            """)
            cursor.execute("""
                INSERT OR IGNORE INTO memories_new (id, user_id, category, content, source, is_enabled, created_at, updated_at)
                SELECT id, 1, category, content, source, is_enabled, created_at, updated_at FROM memories
            """)
            cursor.execute("DROP TABLE memories")
            cursor.execute("ALTER TABLE memories_new RENAME TO memories")

        # Indexes for fast query lookup per user
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, is_pinned, updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id, updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id, is_enabled)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id, due_datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_career_plans_user ON career_plans(user_id, updated_at)")

        conn.commit()


# ---------------- USER AUTHENTICATION & MANAGEMENT ----------------

def validate_registration_inputs(username: str, password: str) -> Tuple[bool, str]:
    """Validate username and password complexity requirements."""
    u = username.strip()
    if not u or len(u) < 3 or len(u) > 30:
        return False, "Username must be between 3 and 30 characters."
    if not re.match(r"^[A-Za-z0-9_.-]+$", u):
        return False, "Username may only contain letters, numbers, underscores, dots, and hyphens."
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    return True, ""

def register_user(username: str, password: str) -> Tuple[bool, str, Optional[int]]:
    """
    Register a new user with salted bcrypt password hashing.
    Returns (success, message, user_id).
    """
    valid, err = validate_registration_inputs(username, password)
    if not valid:
        return False, err, None

    init_db()
    clean_username = username.strip()

    # Hash password with bcrypt and automatic unique salt (12 rounds)
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, updated_at) VALUES (?, ?, ?)",
                (clean_username, hashed, datetime.now().isoformat())
            )
            conn.commit()
            return True, "Account registered successfully!", cursor.lastrowid
        except sqlite3.IntegrityError:
            return False, "Username already exists. Please choose another username.", None
        except Exception as e:
            return False, f"Registration failed: {str(e)}", None

def check_login_rate_limit(username: str) -> Tuple[bool, str]:
    """
    Check in-memory rate limiting per username.
    Prevents brute-force dictionary attacks.
    """
    clean_u = username.strip().lower()
    now = time.time()
    attempts = _LOGIN_ATTEMPTS.get(clean_u, [])
    # Filter attempts within lockout window
    recent_attempts = [t for t in attempts if now - t < LOCKOUT_DURATION_SECONDS]
    _LOGIN_ATTEMPTS[clean_u] = recent_attempts

    if len(recent_attempts) >= MAX_LOGIN_ATTEMPTS:
        wait_time = int(LOCKOUT_DURATION_SECONDS - (now - recent_attempts[0]))
        return False, f"Too many failed login attempts. Please wait {wait_time} seconds before trying again."
    return True, ""

def record_failed_login(username: str):
    """Record a failed login attempt for rate limiting."""
    clean_u = username.strip().lower()
    if clean_u not in _LOGIN_ATTEMPTS:
        _LOGIN_ATTEMPTS[clean_u] = []
    _LOGIN_ATTEMPTS[clean_u].append(time.time())

def clear_failed_login(username: str):
    """Clear failed login attempts upon successful login."""
    clean_u = username.strip().lower()
    if clean_u in _LOGIN_ATTEMPTS:
        del _LOGIN_ATTEMPTS[clean_u]

def authenticate_user(username: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticate user using bcrypt verify with rate-limiting.
    Returns (success, message, user_dict).
    """
    clean_u = username.strip()
    if not clean_u or not password:
        return False, "Username and password are required.", None

    allowed, rate_msg = check_login_rate_limit(clean_u)
    if not allowed:
        return False, rate_msg, None

    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (clean_u,))
        row = cursor.fetchone()

        if not row:
            record_failed_login(clean_u)
            return False, "Invalid username or password.", None

        user = dict(row)
        stored_hash = user["password_hash"].encode("utf-8")

        # Verify password with bcrypt
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            clear_failed_login(clean_u)
            user_data = {
                "id": user["id"],
                "username": user["username"],
                "created_at": user["created_at"]
            }
            return True, "Login successful!", user_data
        else:
            record_failed_login(clean_u)
            return False, "Invalid username or password.", None


# ---------------- MULTI-TENANT CHAT & SESSION CRUD ----------------

def create_session(session_id: str, title: str = "New Chat", user_id: int = 1) -> str:
    """Create a new chat session owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions (id, user_id, title, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET title = excluded.title, updated_at = excluded.updated_at
            WHERE sessions.user_id = excluded.user_id
            """,
            (session_id, user_id, title, datetime.now().isoformat())
        )
        conn.commit()
    return session_id

def update_session_title(session_id: str, title: str, user_id: int = 1) -> bool:
    """Update title for a session owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (title, datetime.now().isoformat(), session_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def get_all_sessions(user_id: int = 1, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all chat sessions for a specific user."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if search_query and search_query.strip():
            param = f"%{search_query.strip()}%"
            cursor.execute(
                """
                SELECT DISTINCT s.* FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id AND m.user_id = s.user_id
                WHERE s.user_id = ? AND (s.title LIKE ? OR m.content LIKE ?)
                ORDER BY s.is_pinned DESC, s.updated_at DESC
                """,
                (user_id, param, param)
            )
        else:
            cursor.execute(
                "SELECT * FROM sessions WHERE user_id = ? ORDER BY is_pinned DESC, updated_at DESC",
                (user_id,)
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def toggle_pin_session(session_id: str, is_pinned: bool, user_id: int = 1) -> bool:
    """Pin or unpin a conversation owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET is_pinned = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (1 if is_pinned else 0, datetime.now().isoformat(), session_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def save_message(
    session_id: str,
    role: str,
    content: str,
    model_used: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    agent_logs: Optional[List[str]] = None,
    activities: Optional[List[Dict[str, Any]]] = None,
    tool_history: Optional[List[Dict[str, Any]]] = None,
    user_id: int = 1
):
    """Store a single chat message owned by user_id."""
    init_db()
    sources_json = json.dumps(sources) if sources else None
    logs_json = json.dumps(agent_logs) if agent_logs else None
    activities_json = json.dumps(activities) if activities else None
    tools_json = json.dumps(tool_history) if tool_history else None

    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        # Verify user ownership of session before inserting message
        cursor.execute("SELECT id FROM sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
        if not cursor.fetchone():
            # Auto-create session under user if not existing
            cursor.execute(
                "INSERT OR IGNORE INTO sessions (id, user_id, title, updated_at) VALUES (?, ?, 'New Chat', ?)",
                (session_id, user_id, datetime.now().isoformat())
            )

        cursor.execute(
            """
            INSERT INTO messages (session_id, user_id, role, content, model_used, sources, agent_logs, activities, tool_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, role, content, model_used, sources_json, logs_json, activities_json, tools_json)
        )
        cursor.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ? AND user_id = ?",
            (datetime.now().isoformat(), session_id, user_id)
        )
        conn.commit()

def get_session_messages(session_id: str, user_id: int = 1) -> List[Dict[str, Any]]:
    """Retrieve all messages for a session strictly owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT m.* FROM messages m
            JOIN sessions s ON m.session_id = s.id
            WHERE m.session_id = ? AND s.user_id = ? AND m.user_id = ?
            ORDER BY m.id ASC
            """,
            (session_id, user_id, user_id)
        )
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            msg = dict(row)
            for field in ["sources", "agent_logs", "activities", "tool_history"]:
                if msg.get(field):
                    try:
                        msg[field] = json.loads(msg[field])
                    except Exception:
                        msg[field] = []
                else:
                    msg[field] = []
            messages.append(msg)
        return messages

def delete_session(session_id: str, user_id: int = 1) -> bool:
    """Delete a session and all its messages owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ? AND user_id = ?", (session_id, user_id))
        cursor.execute("DELETE FROM sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


# ---------------- MULTI-TENANT LONG-TERM MEMORY CRUD ----------------

def create_memory(content: str, category: str = "preference", source: str = "user", user_id: int = 1) -> Optional[int]:
    """Create a persistent memory fact owned by user_id."""
    clean_content = content.strip()
    if not clean_content:
        return None
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO memories (user_id, content, category, source, is_enabled, updated_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (user_id, clean_content, category, source, datetime.now().isoformat())
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Memory already exists for this user - enable and refresh timestamp
            cursor.execute(
                "UPDATE memories SET is_enabled = 1, updated_at = ? WHERE user_id = ? AND content = ?",
                (datetime.now().isoformat(), user_id, clean_content)
            )
            conn.commit()
            return None

def get_all_memories(user_id: int = 1, only_enabled: bool = False) -> List[Dict[str, Any]]:
    """Retrieve memories strictly owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if only_enabled:
            cursor.execute(
                "SELECT * FROM memories WHERE user_id = ? AND is_enabled = 1 ORDER BY updated_at DESC",
                (user_id,)
            )
        else:
            cursor.execute(
                "SELECT * FROM memories WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,)
            )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def update_memory(memory_id: int, content: str, category: str = "preference", is_enabled: bool = True, user_id: int = 1) -> bool:
    """Update a memory item strictly owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE memories
            SET content = ?, category = ?, is_enabled = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (content.strip(), category, 1 if is_enabled else 0, datetime.now().isoformat(), memory_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def delete_memory(memory_id: int, user_id: int = 1) -> bool:
    """Delete a memory item owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ? AND user_id = ?", (memory_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


# ---------------- MULTI-TENANT CAREER PLANNING CRUD ----------------

def create_career_plan(goal_title: str, tasks: List[Dict[str, Any]], total_days: int = 90, user_id: int = 1) -> int:
    """Store a structured career preparation plan owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO career_plans (user_id, goal_title, total_days, tasks_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, goal_title.strip(), total_days, json.dumps(tasks), datetime.now().isoformat())
        )
        conn.commit()
        return cursor.lastrowid

def get_all_career_plans(user_id: int = 1) -> List[Dict[str, Any]]:
    """Retrieve all saved career plans strictly owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM career_plans WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
        rows = cursor.fetchall()
        plans = []
        for r in rows:
            p = dict(r)
            try:
                p["tasks"] = json.loads(p["tasks_json"])
            except Exception:
                p["tasks"] = []
            total = len(p["tasks"])
            completed = sum(1 for t in p["tasks"] if t.get("completed", False))
            p["progress_pct"] = (completed / total * 100.0) if total > 0 else 0.0
            p["total_tasks"] = total
            p["completed_tasks"] = completed
            plans.append(p)
        return plans

def update_career_plan_tasks(plan_id: int, tasks: List[Dict[str, Any]], user_id: int = 1) -> bool:
    """Update tasks state for a career plan owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE career_plans
            SET tasks_json = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (json.dumps(tasks), datetime.now().isoformat(), plan_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def delete_career_plan(plan_id: int, user_id: int = 1) -> bool:
    """Delete a career plan owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM career_plans WHERE id = ? AND user_id = ?", (plan_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


# ---------------- MULTI-TENANT SMART REMINDERS CRUD ----------------

def create_reminder(title: str, due_datetime: str, description: str = "", user_id: int = 1) -> int:
    """Create a persistent reminder owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reminders (user_id, title, description, due_datetime, is_completed, is_notified, updated_at)
            VALUES (?, ?, ?, ?, 0, 0, ?)
            """,
            (user_id, title.strip(), description.strip(), due_datetime.strip(), datetime.now().isoformat())
        )
        conn.commit()
        return cursor.lastrowid

def get_all_reminders(user_id: int = 1) -> List[Dict[str, Any]]:
    """Retrieve all reminders owned by user_id sorted by due datetime."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reminders WHERE user_id = ? ORDER BY due_datetime ASC", (user_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_due_reminders(user_id: int = 1, current_time_iso: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve reminders due now/overdue owned by user_id."""
    init_db()
    now_iso = current_time_iso or datetime.now().isoformat()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM reminders
            WHERE user_id = ? AND is_completed = 0 AND is_notified = 0 AND due_datetime <= ?
            ORDER BY due_datetime ASC
            """,
            (user_id, now_iso)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def mark_reminder_notified(reminder_id: int, user_id: int = 1) -> bool:
    """Mark reminder as notified for user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE reminders SET is_notified = 1, updated_at = ? WHERE id = ? AND user_id = ?",
            (datetime.now().isoformat(), reminder_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def update_reminder(reminder_id: int, title: str, due_datetime: str, description: str = "", is_completed: bool = False, user_id: int = 1) -> bool:
    """Update reminder details owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE reminders
            SET title = ?, due_datetime = ?, description = ?, is_completed = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (title.strip(), due_datetime.strip(), description.strip(), 1 if is_completed else 0, datetime.now().isoformat(), reminder_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def set_reminder_completed(reminder_id: int, is_completed: bool = True, user_id: int = 1) -> bool:
    """Mark a reminder as completed or pending for user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE reminders SET is_completed = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (1 if is_completed else 0, datetime.now().isoformat(), reminder_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def delete_reminder(reminder_id: int, user_id: int = 1) -> bool:
    """Delete a reminder owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


# ---------------- MULTI-TENANT SMART NOTES CRUD ----------------

def create_note(title: str, content: str, session_id: Optional[str] = None, tags: str = "", user_id: int = 1) -> int:
    """Create a new smart note owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO notes (user_id, session_id, title, content, tags, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, session_id, title, content, tags, datetime.now().isoformat())
        )
        conn.commit()
        return cursor.lastrowid

def update_note(note_id: int, title: str, content: str, tags: str = "", user_id: int = 1) -> bool:
    """Update an existing note owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE notes
            SET title = ?, content = ?, tags = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (title, content, tags, datetime.now().isoformat(), note_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def delete_note(note_id: int, user_id: int = 1) -> bool:
    """Delete a note owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def get_all_notes(user_id: int = 1, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all notes strictly owned by user_id."""
    init_db()
    with sqlite3.connect(settings.DB_PATH, timeout=20.0) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if search_query and search_query.strip():
            param = f"%{search_query.strip()}%"
            cursor.execute(
                """
                SELECT * FROM notes
                WHERE user_id = ? AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)
                ORDER BY updated_at DESC
                """,
                (user_id, param, param, param)
            )
        else:
            cursor.execute("SELECT * FROM notes WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
