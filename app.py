import streamlit as st
import uuid
from config.settings import settings
from database.db import (
    init_db,
    register_user,
    authenticate_user,
    create_session,
    get_all_sessions,
    get_session_messages,
    save_message,
    delete_session,
    update_session_title,
    toggle_pin_session,
    create_note,
    update_note,
    delete_note,
    get_all_notes,
    create_memory,
    get_all_memories,
    update_memory,
    delete_memory,
    create_reminder,
    get_all_reminders,
    get_due_reminders,
    mark_reminder_notified,
    update_reminder,
    set_reminder_completed,
    delete_reminder,
    create_career_plan,
    get_all_career_plans,
    update_career_plan_tasks,
    delete_career_plan
)
from agent.core import UniversalAgent
from utils.helpers import truncate_text
from tools.productivity_pdf import extract_text_from_pdf, summarize_pdf_text, answer_pdf_question
from tools.productivity_excel import load_tabular_file, answer_tabular_question, generate_data_chart
from tools.productivity_docs import create_pdf_document, create_docx_document, create_excel_document
from tools.productivity_code import generate_code_solution, explain_code_snippet, debug_code_error
from tools.career_research import (
    run_deep_research,
    research_job_opportunities,
    analyze_skill_gap,
    generate_learning_roadmap
)

# Page Configuration
st.set_page_config(
    page_title="Universal AI Agent",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Dark Theme Styling with Red Accents & High Contrast
st.markdown("""
<style>
    /* Global App Background & Base Typography */
    .stApp {
        background-color: #0b0e14;
        color: #f0f6fc;
    }
    
    /* Global Headings & Markdown Text */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }
    p, span, label, div {
        color: #e6edf3;
    }
    
    /* Sidebar Styling & Visibility */
    section[data-testid="stSidebar"] {
        background-color: #121721 !important;
        border-right: 1px solid #2d333b !important;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] .stSubheader {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: #e6edf3 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: #adb5bd !important;
        font-weight: 500;
    }
    
    /* Dividers */
    hr {
        border-color: #30363d !important;
        margin: 1.2rem 0 !important;
    }

    /* Primary Red Accent Button (New Chat) */
    button[kind="primary"] {
        background: linear-gradient(135deg, #e63946 0%, #c1121f 100%) !important;
        color: #ffffff !important;
        border: 1px solid #ff4d5a !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        box-shadow: 0 3px 10px rgba(230, 57, 70, 0.3) !important;
        transition: all 0.25s ease-in-out !important;
    }
    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #f04452 0%, #d90429 100%) !important;
        border-color: #ff6b77 !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 5px 14px rgba(230, 57, 70, 0.45) !important;
    }

    /* Secondary / Session Navigation Buttons */
    button[kind="secondary"] {
        background-color: #1a202c !important;
        color: #e6edf3 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        text-align: left !important;
        transition: all 0.2s ease !important;
    }
    button[kind="secondary"]:hover {
        background-color: #242c3d !important;
        color: #ffffff !important;
        border-color: #e63946 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4) !important;
    }

    /* Selectbox & Dropdown Visibility */
    div[data-baseweb="select"] {
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #161b24 !important;
        border: 1px solid #30363d !important;
        color: #f0f6fc !important;
        font-weight: 500 !important;
    }
    div[data-baseweb="select"] > div:hover,
    div[data-baseweb="select"] > div:focus-within {
        border-color: #e63946 !important;
        box-shadow: 0 0 0 2px rgba(230, 57, 70, 0.2) !important;
    }
    div[data-baseweb="popover"] ul,
    div[data-baseweb="menu"] {
        background-color: #161b24 !important;
        border: 1px solid #30363d !important;
    }
    div[data-baseweb="menu"] li {
        color: #e6edf3 !important;
    }
    div[data-baseweb="menu"] li:hover {
        background-color: #261f26 !important;
        color: #ff6b77 !important;
    }

    /* Chat Messages - Elevated readability and contrast */
    div[data-testid="stChatMessage"] {
        background-color: #151a23 !important;
        border: 1px solid #28303e !important;
        border-radius: 12px !important;
        padding: 1rem 1.25rem !important;
        margin-bottom: 0.85rem !important;
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.25) !important;
    }
    /* Distinct User Message Accent */
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),
    div[data-testid="stChatMessage"]:has(span:contains("🧑‍💻")) {
        background-color: #19202c !important;
        border-left: 3px solid #e63946 !important;
    }
    div[data-testid="stChatMessage"] p {
        color: #f0f6fc !important;
        font-size: 0.96rem !important;
        line-height: 1.6 !important;
    }

    /* Bottom Chat Input Bar */
    div[data-testid="stChatInput"] {
        border-radius: 12px !important;
    }
    div[data-testid="stChatInput"] > div {
        background-color: #151a23 !important;
        border: 1px solid #384252 !important;
        color: #f0f6fc !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stChatInput"] > div:focus-within {
        border-color: #e63946 !important;
        box-shadow: 0 0 0 2px rgba(230, 57, 70, 0.3) !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #ffffff !important;
        font-size: 0.95rem !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder {
        color: #8b949e !important;
    }
    div[data-testid="stChatInput"] button {
        color: #e63946 !important;
        transition: transform 0.15s ease !important;
    }
    div[data-testid="stChatInput"] button:hover {
        transform: scale(1.1) !important;
        color: #ff4d5a !important;
    }

    /* Status Indicators & Model Badges */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #1a212d;
        border: 1px solid #384354;
        padding: 4px 11px;
        border-radius: 16px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-top: 6px;
        margin-bottom: 8px;
    }
    .badge-gemini {
        color: #93b5ff;
        border-color: rgba(147, 181, 255, 0.35);
        background-color: #131b2c;
    }
    .badge-groq {
        color: #ff9e42;
        border-color: rgba(255, 158, 66, 0.35);
        background-color: #241a14;
    }

    /* Web Source Tags */
    .source-tag {
        display: inline-block;
        background-color: #182335;
        color: #79c0ff;
        border: 1px solid #388bfd44;
        padding: 4px 10px;
        margin: 4px 5px 4px 0;
        border-radius: 8px;
        font-size: 0.82rem;
        font-weight: 500;
        text-decoration: none;
        transition: all 0.2s ease;
    }
    .source-tag:hover {
        background-color: #20314d;
        color: #a5d6ff;
        border-color: #58a6ff;
        text-decoration: none;
        transform: translateY(-1px);
    }

    /* Agent Activity / Trace Expander */
    div[data-testid="stExpander"] {
        background-color: #121721 !important;
        border: 1px solid #2d3644 !important;
        border-radius: 8px !important;
        margin-top: 8px !important;
    }
    div[data-testid="stExpander"] summary {
        color: #e6edf3 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stExpander"] summary:hover {
        color: #e63946 !important;
    }
    div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] code {
        background-color: #0b0e14 !important;
        color: #38bdf8 !important;
        border: 1px solid #1f2937 !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-size: 0.85rem !important;
    }

    /* Status Box (While agent is thinking) */
    div[data-testid="stStatusWidget"] {
        background-color: #151a23 !important;
        border: 1px solid #2e3848 !important;
        border-radius: 10px !important;
    }

    /* API Status Pill in Sidebar */
    .api-status-box {
        background-color: #171d28;
        border: 1px solid #2d3644;
        border-radius: 8px;
        padding: 8px 4px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if "session_token" not in st.session_state:
    st.session_state.session_token = None

if "login_time" not in st.session_state:
    st.session_state.login_time = None

# Session Expiration Check (24 hours inactivity timeout)
SESSION_MAX_AGE_SECONDS = 86400  # 24 hours
if st.session_state.authenticated_user and st.session_state.login_time:
    import time as _t
    if _t.time() - st.session_state.login_time > SESSION_MAX_AGE_SECONDS:
        st.session_state.authenticated_user = None
        st.session_state.session_token = None
        st.session_state.login_time = None
        st.warning("Your session has expired. Please sign in again.")

# ---------------- AUTHENTICATION GATE ----------------
if not st.session_state.authenticated_user:
    st.markdown("""
        <div style="text-align: center; margin-top: 2rem; margin-bottom: 2rem;">
            <h1 style="font-size: 2.8rem; margin-bottom: 0.2rem;">🌌 Universal AI Agent</h1>
            <p style="color: #8b949e; font-size: 1.1rem;">Secure Multi-User Autonomous AI & Productivity Platform</p>
        </div>
    """, unsafe_allow_html=True)

    auth_col1, auth_col2, auth_col3 = st.columns([1, 1.8, 1])
    with auth_col2:
        tab_login, tab_register = st.tabs(["🔐 Sign In", "📝 Create Account"])

        with tab_login:
            st.markdown("#### Welcome Back")
            login_user = st.text_input("Username", key="login_username_input", placeholder="Enter your username")
            login_pass = st.text_input("Password", type="password", key="login_password_input", placeholder="Enter your password")

            if st.button("🚀 Sign In", type="primary", use_container_width=True, key="btn_signin"):
                success, msg, user_data = authenticate_user(login_user, login_pass)
                if success and user_data:
                    import time as _t
                    st.session_state.authenticated_user = user_data
                    st.session_state.session_token = str(uuid.uuid4())
                    st.session_state.login_time = _t.time()
                    st.success(f"Welcome back, **{user_data['username']}**!")
                    st.rerun()
                else:
                    st.error(f"⚠️ {msg}")

        with tab_register:
            st.markdown("#### New Account Registration")
            st.caption("Create your isolated personal workspace. Passwords are encrypted with salted bcrypt hashes.")
            reg_user = st.text_input("Choose Username", key="reg_username_input", placeholder="3-30 letters/numbers")
            reg_pass = st.text_input("Choose Password", type="password", key="reg_password_input", placeholder="At least 8 characters")
            reg_pass_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm_input", placeholder="Re-type your password")

            if st.button("✨ Create Account", type="primary", use_container_width=True, key="btn_signup"):
                if reg_pass != reg_pass_confirm:
                    st.error("Passwords do not match. Please verify your password confirmation.")
                else:
                    success, msg, new_uid = register_user(reg_user, reg_pass)
                    if success and new_uid:
                        import time as _t
                        st.session_state.authenticated_user = {"id": new_uid, "username": reg_user.strip()}
                        st.session_state.session_token = str(uuid.uuid4())
                        st.session_state.login_time = _t.time()
                        st.success("🎉 Account created successfully! Launching your workspace...")
                        st.rerun()
                    else:
                        st.error(f"⚠️ {msg}")

    # Stop execution here if not authenticated
    st.stop()

# Current Active User ID
current_user = st.session_state.authenticated_user
current_user_id = current_user["id"]

# Initialize User-Scoped Session State
if "current_session_id" not in st.session_state or not st.session_state.current_session_id:
    init_db()
    existing_sessions = get_all_sessions(user_id=current_user_id)
    if existing_sessions:
        st.session_state.current_session_id = existing_sessions[0]["id"]
    else:
        new_id = str(uuid.uuid4())
        create_session(new_id, "New Chat", user_id=current_user_id)
        st.session_state.current_session_id = new_id

if "agent" not in st.session_state:
    st.session_state.agent = UniversalAgent()

if "preferred_model" not in st.session_state:
    st.session_state.preferred_model = "auto"

if "current_view" not in st.session_state:
    st.session_state.current_view = "chat"

if "memory_enabled" not in st.session_state:
    st.session_state.memory_enabled = True

if "chat_search" not in st.session_state:
    st.session_state.chat_search = ""

# In-app Reminder Notification Check (User-Scoped)
due_reminders = get_due_reminders(user_id=current_user_id)
if due_reminders:
    for r in due_reminders:
        st.toast(f"🔔 **Reminder Due!** {r['title']}", icon="⏰")
        mark_reminder_notified(r["id"], user_id=current_user_id)

# Sidebar Navigation
with st.sidebar:
    st.title("🌌 Universal Agent")
    
    # Authenticated User Badge & Logout
    st.markdown(f"""
        <div style="background-color: #171d28; border: 1px solid #30363d; border-radius: 8px; padding: 8px 12px; margin-bottom: 12px;">
            <div style="font-size: 0.8rem; color: #8b949e;">Signed in as</div>
            <div style="font-weight: 700; color: #ffffff; font-size: 1.05rem;">👤 {current_user['username']}</div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Sign Out", use_container_width=True, key="btn_signout"):
        st.session_state.authenticated_user = None
        st.session_state.session_token = None
        st.session_state.login_time = None
        st.session_state.current_session_id = None
        st.rerun()

    st.caption("Phase 3: Autonomous AI + Multi-User Isolation")

    # Mode Selector
    st.subheader("🛠️ Workspace Tools")
    view_options = {
        "chat": "💬 Autonomous Chat",
        "deep_research": "🔬 Deep Research",
        "jobs": "💼 Job Opportunities",
        "skill_gap": "🎯 Skill Gap Analyzer",
        "roadmap": "🗺️ Learning Roadmap",
        "career_plan": "📋 90-Day Planning Mode",
        "memory": "🧠 Long-Term Memory",
        "reminders": "⏰ Smart Reminders",
        "pdf": "📄 PDF Assistant",
        "excel": "📊 Excel & CSV Assistant",
        "docs": "📝 Document Creator",
        "code": "💻 Coding Assistant",
        "notes": "📓 Smart Notes"
    }
    selected_view = st.selectbox(
        "Workspace View",
        options=list(view_options.keys()),
        format_func=lambda x: view_options[x],
        index=list(view_options.keys()).index(st.session_state.current_view)
    )
    st.session_state.current_view = selected_view

    st.divider()

    # New Chat Button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        create_session(new_id, "New Chat", user_id=current_user_id)
        st.session_state.current_session_id = new_id
        st.session_state.current_view = "chat"
        st.rerun()

    st.divider()

    # Model & Routing Selection
    st.subheader("⚙️ Settings & Preferences")
    mem_toggle = st.toggle("🧠 Long-Term Memory Active", value=st.session_state.memory_enabled)
    st.session_state.memory_enabled = mem_toggle

    model_choice = st.selectbox(
        "Routing Priority",
        options=["auto", "gemini", "groq"],
        format_func=lambda x: {
            "auto": "✨ Auto (Gemini Primary → Groq Fallback)",
            "gemini": "🔵 Gemini (gemini-3.8-flash)",
            "groq": "⚡ Groq (openai/gpt-oss-120b)"
        }[x],
        index=0 if st.session_state.preferred_model == "auto" else (1 if st.session_state.preferred_model == "gemini" else 2)
    )
    st.session_state.preferred_model = model_choice

    # API Key Configuration Status
    st.markdown("### 🔑 API Status")
    settings.reload()
    key_status = settings.validate_keys()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("Gemini")
        st.markdown(f"<div class='api-status-box'>{'🟢 Active' if key_status['gemini'] else '🔴 Missing'}</div>", unsafe_allow_html=True)
    with col2:
        st.caption("Groq")
        st.markdown(f"<div class='api-status-box'>{'🟢 Active' if key_status['groq'] else '🔴 Missing'}</div>", unsafe_allow_html=True)
    with col3:
        st.caption("Tavily")
        st.markdown(f"<div class='api-status-box'>{'🟢 Active' if key_status['tavily'] else '🔴 Missing'}</div>", unsafe_allow_html=True)

    if not all(key_status.values()):
        st.warning("One or more keys are missing. Please add them to your `.env` file.", icon="⚠️")

    st.divider()

    # Advanced Chat History Management
    st.subheader("💬 Chat Management")
    chat_filter = st.text_input("🔍 Search chats", placeholder="Filter by keyword...", key="chat_search_input")
    sessions = get_all_sessions(user_id=current_user_id, search_query=chat_filter)
    
    for s in sessions:
        is_pinned = bool(s.get("is_pinned", 0))
        is_active = (s["id"] == st.session_state.current_session_id)
        pin_icon = "📌 " if is_pinned else ""
        active_prefix = "▶ " if is_active else ""
        btn_label = f"{pin_icon}{active_prefix}{s['title']}"
        
        c_btn, c_pin, c_del = st.columns([0.68, 0.16, 0.16])
        with c_btn:
            if st.button(btn_label, key=f"session_{s['id']}", use_container_width=True):
                st.session_state.current_session_id = s["id"]
                st.session_state.current_view = "chat"
                st.rerun()
        with c_pin:
            pin_title = "Unpin" if is_pinned else "Pin"
            if st.button("📍" if is_pinned else "📌", key=f"pin_{s['id']}", help=f"{pin_title} chat"):
                toggle_pin_session(s["id"], not is_pinned, user_id=current_user_id)
                st.rerun()
        with c_del:
            if st.button("🗑️", key=f"del_{s['id']}", help="Delete chat"):
                delete_session(s["id"], user_id=current_user_id)
                remaining = get_all_sessions(user_id=current_user_id)
                if remaining:
                    st.session_state.current_session_id = remaining[0]["id"]
                else:
                    new_id = str(uuid.uuid4())
                    create_session(new_id, "New Chat", user_id=current_user_id)
                    st.session_state.current_session_id = new_id
                st.rerun()

# Main View Router
current_view = st.session_state.current_view

if current_view == "deep_research":
    st.header("🔬 Deep Research Assistant")
    st.caption("Perform multi-query deep web research with deconstructed queries, verified web sources, and exportable structured reports.")
    
    res_topic = st.text_input("Research Topic or Complex Question:", placeholder="e.g. State of generative AI agents in enterprise production 2025-2026")
    col_q1, col_q2 = st.columns([0.5, 0.5])
    with col_q1:
        num_queries = st.slider("Depth (Number of focused sub-queries)", min_value=2, max_value=4, value=3)
    
    if st.button("🚀 Begin Deep Research", type="primary") and res_topic:
        with st.status("🔍 Deep Research in progress...", expanded=True) as status_box:
            status_box.write("1. Deconstructing research topic into sub-queries...")
            res_data = run_deep_research(topic=res_topic, max_subqueries=num_queries, preferred_model=st.session_state.preferred_model)
            status_box.write(f"2. Gathered verified findings from {len(res_data.get('sources', []))} unique sources.")
            status_box.write("3. Synthesizing structured research report...")
            status_box.update(label="Research Complete!", state="complete", expanded=False)
            
        if res_data["success"]:
            st.session_state.latest_research_report = res_data
            
    if "latest_research_report" in st.session_state:
        rep = st.session_state.latest_research_report
        st.markdown(f"### 📋 Research Findings: {rep['topic']}")
        
        # Sources and Subqueries expander
        with st.expander("🌐 Sub-Queries & Verified Sources", expanded=False):
            st.markdown("**Sub-Queries Explored:**")
            for sq in rep.get("subqueries", []):
                st.markdown(f"- `{sq}`")
            st.markdown("**Verified Sources:**")
            for s in rep.get("sources", []):
                st.markdown(f"- [{s.get('title')}]({s.get('url')})")

        st.markdown(rep["report"])
        
        # Export Report buttons using existing Document Creator
        st.divider()
        st.markdown("##### 📥 Export Research Report")
        col_exp1, col_exp2 = st.columns(2)
        safe_name = rep['topic'].lower().replace(' ', '_')[:30]
        with col_exp1:
            pdf_bytes = create_pdf_document(f"Research: {rep['topic']}", rep["report"])
            st.download_button("⬇️ Download as PDF", data=pdf_bytes, file_name=f"{safe_name}_report.pdf", mime="application/pdf")
        with col_exp2:
            docx_bytes = create_docx_document(f"Research: {rep['topic']}", rep["report"])
            st.download_button("⬇️ Download as Word (.docx)", data=docx_bytes, file_name=f"{safe_name}_report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

elif current_view == "jobs":
    st.header("💼 Job Opportunities Research")
    st.caption("Search real-time active technical job openings using live web search and extract structured job requirements.")
    
    col_j1, col_j2, col_j3 = st.columns(3)
    with col_j1:
        target_role = st.selectbox("Role Target", options=["Python Developer", "Data Analyst", "AI/ML Engineer", "Full Stack Developer", "Backend Engineer", "Cloud Architect"])
    with col_j2:
        loc_pref = st.text_input("Preferred Location", placeholder="e.g. Remote, New York, London, Bangalore")
    with col_j3:
        exp_lvl = st.selectbox("Experience Level", options=["Entry-Level", "Mid-Level", "Senior", "Lead / Staff"])
        
    if st.button("🔍 Search Job Postings", type="primary"):
        with st.spinner("Searching live web postings for verified job openings..."):
            job_res = research_job_opportunities(role=target_role, location=loc_pref, experience_level=exp_lvl, preferred_model=st.session_state.preferred_model)
            
        if not job_res["success"] or not job_res.get("jobs"):
            st.warning("No structured job postings could be extracted from search results. See sources below.")
            if job_res.get("sources"):
                for s in job_res["sources"]:
                    st.markdown(f"- [{s.get('title')}]({s.get('url')})")
        else:
            st.success(f"✅ Found **{len(job_res['jobs'])}** verified job listings!")
            for j in job_res["jobs"]:
                with st.container():
                    st.markdown(f"### {j.get('job_title', target_role)}")
                    st.caption(f"🏢 **{j.get('company', 'Not specified')}** | 📍 **{j.get('location', 'Not specified')}** | ⏳ **Experience**: {j.get('experience_required', 'Not specified')}")
                    if j.get("required_skills"):
                        skills_str = " ".join([f"`{s}`" for s in j["required_skills"]])
                        st.markdown(f"**Required Skills**: {skills_str}")
                    if j.get("source_url"):
                        st.markdown(f"[🔗 View Original Job Posting]({j['source_url']})")
                    st.divider()

elif current_view == "skill_gap":
    st.header("🎯 Skill Gap Analyzer")
    st.caption("Compare your current skillset against market requirements for your target role and get a prioritized learning roadmap.")
    
    col_sg1, col_sg2 = st.columns(2)
    with col_sg1:
        sg_role = st.selectbox("Target Role", options=["Python Developer", "AI/ML Engineer", "Data Analyst", "Full Stack Developer", "DevOps Engineer"], key="sg_role_select")
        sg_level = st.selectbox("Target Experience Level", options=["Junior / Entry-Level", "Mid-Level", "Senior / Lead"], key="sg_level_select")
    with col_sg2:
        curr_skills = st.text_area("Your Current Skills (comma separated or bullet points):", placeholder="e.g. Python, SQL, Git, Basic Pandas, REST APIs", height=120)
        
    if st.button("📊 Analyze Skill Gap", type="primary") and curr_skills:
        with st.spinner("Analyzing market demands vs your current skills..."):
            sg_res = analyze_skill_gap(current_skills=curr_skills, target_role=sg_role, experience_level=sg_level, preferred_model=st.session_state.preferred_model)
            if sg_res.get("success"):
                st.markdown(sg_res["content"])
            else:
                st.error(f"Analysis error: {sg_res.get('error')}")

elif current_view == "roadmap":
    st.header("🗺️ Learning Roadmap Generator")
    st.caption("Generate personalized daily and weekly study curriculums tailored to your available hours and target duration.")
    
    col_rm1, col_rm2, col_rm3 = st.columns(3)
    with col_rm1:
        target_subject = st.text_input("Skill / Career Target", value="Python Backend & FastAPI")
    with col_rm2:
        duration_days = st.slider("Target Duration (Days)", min_value=14, max_value=90, value=30, step=7)
    with col_rm3:
        daily_hrs = st.slider("Available Study Hours / Day", min_value=1.0, max_value=8.0, value=2.0, step=0.5)
        
    if st.button("🚀 Generate Roadmap", type="primary"):
        with st.spinner("Designing comprehensive daily & weekly learning curriculum..."):
            rm_res = generate_learning_roadmap(target_skill=target_subject, target_duration_days=duration_days, daily_hours=daily_hrs, preferred_model=st.session_state.preferred_model)
            if rm_res.get("success"):
                st.markdown(rm_res["content"])
            else:
                st.error(f"Roadmap error: {rm_res.get('error')}")

elif current_view == "career_plan":
    st.header("📋 90-Day Planning & Goal Tracker")
    st.caption("Break complex career goals into structured milestone tasks with deadlines, priorities, and SQLite progress tracking.")
    
    with st.expander("➕ Generate New Career Preparation Plan", expanded=len(get_all_career_plans()) == 0):
        plan_goal = st.text_input("Career Goal Description", value="Prepare me for a Python Developer job in 90 days")
        plan_days = st.selectbox("Plan Duration", options=[30, 60, 90], index=2)
        
        if st.button("🎯 Build & Save Plan", type="primary"):
            with st.spinner("Breaking goal into actionable milestones & tasks..."):
                plan_prompt = f"""Break down this career goal into 6 to 10 actionable, high-impact tasks across {plan_days} days:
Goal: "{plan_goal}"

For each task, return:
- title: concise task name
- phase: (e.g. Month 1, Month 2, Month 3 or Week 1-2)
- priority: High, Medium, or Low
- deadline_day: approximate target day (e.g. Day 15, Day 30)

Respond ONLY with valid JSON array:
[
  {{"title": "...", "phase": "...", "priority": "High", "deadline_day": "Day 15", "completed": false}}
]
"""
                plan_res = query_llm_with_fallback(plan_prompt, "Output valid JSON array of tasks only.", preferred_model=st.session_state.preferred_model)
                tasks = []
                if plan_res.get("success"):
                    try:
                        content = plan_res["content"].strip()
                        start = content.find("[")
                        end = content.rfind("]")
                        if start != -1 and end != -1:
                            tasks = json.loads(content[start:end+1])
                    except Exception:
                        pass
                
                if not tasks:
                    tasks = [
                        {"title": "Core Python OOP & Data Structures", "phase": "Month 1", "priority": "High", "deadline_day": "Day 30", "completed": False},
                        {"title": "FastAPI & SQLite Web Services", "phase": "Month 2", "priority": "High", "deadline_day": "Day 60", "completed": False},
                        {"title": "Full Portfolio Project & Interview Prep", "phase": "Month 3", "priority": "High", "deadline_day": "Day 90", "completed": False}
                    ]
                create_career_plan(goal_title=plan_goal, tasks=tasks, total_days=plan_days, user_id=current_user_id)
                st.success("Career preparation plan created!")
                st.rerun()

    st.divider()
    saved_plans = get_all_career_plans(user_id=current_user_id)
    st.markdown(f"##### Active Career Plans ({len(saved_plans)})")
    
    if not saved_plans:
        st.info("No career plans created yet. Use the form above to generate your first plan.")
    else:
        for p in saved_plans:
            with st.container():
                st.markdown(f"### 🎯 {p['goal_title']} ({p['total_days']} Days)")
                st.progress(p["progress_pct"] / 100.0)
                st.caption(f"Progress: **{p['completed_tasks']} / {p['total_tasks']}** tasks completed ({p['progress_pct']:.1f}%) | Created: {p['created_at']}")
                
                # Render tasks with interactive checkboxes
                tasks = p["tasks"]
                tasks_modified = False
                for idx, t in enumerate(tasks):
                    c_chk, c_meta = st.columns([0.75, 0.25])
                    with c_chk:
                        is_done = st.checkbox(
                            f"**{t.get('title')}** ({t.get('phase', 'Phase')})",
                            value=t.get("completed", False),
                            key=f"plan_{p['id']}_task_{idx}"
                        )
                        if is_done != t.get("completed", False):
                            tasks[idx]["completed"] = is_done
                            tasks_modified = True
                    with c_meta:
                        st.caption(f"Priority: `{t.get('priority', 'Med')}` | ⏰ `{t.get('deadline_day', '')}`")
                
                if tasks_modified:
                    update_career_plan_tasks(p["id"], tasks, user_id=current_user_id)
                    st.rerun()
                    
                if st.button("🗑️ Delete Plan", key=f"del_plan_{p['id']}"):
                    delete_career_plan(p["id"], user_id=current_user_id)
                    st.rerun()
                st.divider()

elif current_view == "memory":
    st.header("🧠 Long-Term Memory Management")
    st.caption("Manage user preferences and learned facts that the autonomous agent remembers across sessions.")
    
    # Enable/Disable Master Toggle
    mem_status = "🟢 Active" if st.session_state.memory_enabled else "🔴 Disabled"
    st.markdown(f"**Memory Status**: {mem_status}")
    
    with st.expander("➕ Save New Memory Manually", expanded=False):
        new_mem_content = st.text_input("Memory Fact / User Preference", placeholder="e.g. User prefers concise answers with Python code examples.")
        new_mem_cat = st.selectbox("Category", options=["preference", "personal", "work", "technical"])
        if st.button("💾 Save Memory", type="primary") and new_mem_content:
            create_memory(content=new_mem_content, category=new_mem_cat, source="user_manual", user_id=current_user_id)
            st.success("Memory saved successfully!")
            st.rerun()

    st.divider()
    all_mems = get_all_memories(user_id=current_user_id)
    st.markdown(f"##### Stored Memories ({len(all_mems)})")
    
    if not all_mems:
        st.info("No long-term memories stored yet. You can add one above or tell the agent 'Remember that I prefer...' during chat.")
    else:
        for m in all_mems:
            with st.container():
                c_txt, c_toggle, c_del = st.columns([0.7, 0.15, 0.15])
                with c_txt:
                    badge_style = "color: #58a6ff; font-size: 0.8rem;"
                    st.markdown(f"**{m['content']}**")
                    st.caption(f"Category: `{m.get('category', 'general')}` | Source: `{m.get('source', 'user')}` | Created: {m['created_at']}")
                with c_toggle:
                    is_en = bool(m.get("is_enabled", 1))
                    toggle_label = "Active" if is_en else "Inactive"
                    if st.button(toggle_label, key=f"mem_toggle_{m['id']}", help="Enable/Disable this memory"):
                        update_memory(m["id"], content=m["content"], category=m["category"], is_enabled=not is_en, user_id=current_user_id)
                        st.rerun()
                with c_del:
                    if st.button("🗑️", key=f"del_mem_{m['id']}", help="Delete memory"):
                        delete_memory(m["id"], user_id=current_user_id)
                        st.rerun()
                st.divider()

elif current_view == "reminders":
    st.header("⏰ Smart Reminders")
    st.caption("Local persistent reminder system with in-app alerts when due. (Requires application to be open).")
    
    with st.expander("➕ Add New Reminder", expanded=True):
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            rem_title = st.text_input("Reminder Title", placeholder="e.g. Team standup or Submit quarterly report")
            rem_desc = st.text_area("Description (optional)", placeholder="Notes or agenda...")
        with col_r2:
            import datetime as dt
            rem_date = st.date_input("Due Date", min_value=dt.date.today())
            rem_time = st.time_input("Due Time", value=dt.datetime.now().time())
            
        if st.button("🔔 Set Reminder", type="primary") and rem_title:
            due_dt_combined = dt.datetime.combine(rem_date, rem_time)
            due_iso = due_dt_combined.isoformat()
            create_reminder(title=rem_title, due_datetime=due_iso, description=rem_desc, user_id=current_user_id)
            st.success(f"Reminder set for {due_dt_combined.strftime('%Y-%m-%d %I:%M %p')}!")
            st.rerun()

    st.divider()
    all_rems = get_all_reminders(user_id=current_user_id)
    now_iso = dt.datetime.now().isoformat()
    
    # Categorize reminders
    upcoming = [r for r in all_rems if not r["is_completed"] and r["due_datetime"] > now_iso]
    overdue = [r for r in all_rems if not r["is_completed"] and r["due_datetime"] <= now_iso]
    completed = [r for r in all_rems if r["is_completed"]]
    
    tab_up, tab_over, tab_comp = st.tabs([f"📅 Upcoming ({len(upcoming)})", f"⚠️ Overdue / Due ({len(overdue)})", f"✅ Completed ({len(completed)})"])
    
    with tab_up:
        for r in upcoming:
            with st.container():
                c1, c2, c3 = st.columns([0.7, 0.15, 0.15])
                with c1:
                    st.markdown(f"**{r['title']}**")
                    if r.get("description"):
                        st.caption(r["description"])
                    st.caption(f"⏰ Due: `{r['due_datetime']}`")
                with c2:
                    if st.button("Mark Done", key=f"comp_{r['id']}"):
                        set_reminder_completed(r["id"], True, user_id=current_user_id)
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"del_rem_{r['id']}"):
                        delete_reminder(r["id"], user_id=current_user_id)
                        st.rerun()
                st.divider()

    with tab_over:
        for r in overdue:
            with st.container():
                c1, c2, c3 = st.columns([0.7, 0.15, 0.15])
                with c1:
                    st.markdown(f"🔴 **{r['title']}** (Due/Overdue)")
                    if r.get("description"):
                        st.caption(r["description"])
                    st.caption(f"⏰ Due: `{r['due_datetime']}`")
                with c2:
                    if st.button("Mark Done", key=f"comp_over_{r['id']}"):
                        set_reminder_completed(r["id"], True, user_id=current_user_id)
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"del_rem_over_{r['id']}"):
                        delete_reminder(r["id"], user_id=current_user_id)
                        st.rerun()
                st.divider()

    with tab_comp:
        for r in completed:
            with st.container():
                c1, c2 = st.columns([0.85, 0.15])
                with c1:
                    st.markdown(f"~~{r['title']}~~")
                    st.caption(f"Completed | Was due: `{r['due_datetime']}`")
                with c2:
                    if st.button("🗑️", key=f"del_rem_comp_{r['id']}"):
                        delete_reminder(r["id"], user_id=current_user_id)
                        st.rerun()
                st.divider()

elif current_view == "pdf":
    st.header("📄 PDF Assistant")
    st.caption("Upload any PDF to extract text, generate structured executive summaries, and ask in-depth questions.")
    
    uploaded_pdf = st.file_uploader("Upload PDF Document", type=["pdf"], key="pdf_uploader")
    if uploaded_pdf:
        pdf_bytes = uploaded_pdf.read()
        extracted = extract_text_from_pdf(pdf_bytes, filename=uploaded_pdf.name)
        
        if not extracted["success"]:
            st.error(f"⚠️ {extracted['error']}", icon="🚫")
        else:
            st.success(f"✅ Extracted **{extracted['total_pages']}** page(s) and **{extracted['char_count']:,}** characters.")
            
            tab1, tab2, tab3 = st.tabs(["📝 Summary", "❓ Ask Questions", "🔍 Raw Extracted Content"])
            with tab1:
                if st.button("✨ Generate Document Summary", type="primary"):
                    with st.spinner("Analyzing document structure & synthesizing summary..."):
                        summary_res = summarize_pdf_text(extracted["text"], preferred_model=st.session_state.preferred_model)
                        if summary_res.get("success"):
                            st.markdown(summary_res["content"])
                        else:
                            st.error(f"Summary generation error: {summary_res.get('error')}")
            with tab2:
                pdf_q = st.text_input("Ask a question about this PDF:", placeholder="e.g. What were the key conclusions?")
                if st.button("🔍 Get Answer", key="btn_pdf_q") and pdf_q:
                    with st.spinner("Analyzing document context..."):
                        ans_res = answer_pdf_question(extracted["text"], pdf_q, preferred_model=st.session_state.preferred_model)
                        if ans_res.get("success"):
                            st.markdown(ans_res["content"])
                        else:
                            st.error(f"Error answering question: {ans_res.get('error')}")
            with tab3:
                st.text_area("Extracted Document Text", value=extracted["text"][:12000], height=350)

elif current_view == "excel":
    st.header("📊 Excel & CSV Data Assistant")
    st.caption("Upload Excel (.xlsx) or CSV files for automated statistical analysis, question answering, and charting.")
    
    uploaded_file = st.file_uploader("Upload Spreadsheet", type=["csv", "xlsx", "xls"], key="tabular_uploader")
    if uploaded_file:
        tab_data = load_tabular_file(uploaded_file.read(), filename=uploaded_file.name)
        if not tab_data["success"]:
            st.error(f"⚠️ {tab_data['error']}", icon="🚫")
        else:
            df = tab_data["df"]
            st.success(f"✅ Loaded **{tab_data['rows']}** rows and **{len(tab_data['columns'])}** columns. Missing values: **{tab_data['missing_values']}**.")
            st.dataframe(df.head(10), use_container_width=True)
            
            tab1, tab2, tab3 = st.tabs(["📈 Quick Calculations", "❓ Data Q&A", "📊 Chart Generator"])
            with tab1:
                st.markdown("##### Column Statistics")
                if tab_data["summary_stats"]:
                    stats_list = []
                    for col, s in tab_data["summary_stats"].items():
                        stats_list.append({
                            "Column": col,
                            "Sum": f"{s['sum']:,.2f}",
                            "Average": f"{s['mean']:,.2f}",
                            "Min": f"{s['min']:,.2f}",
                            "Max": f"{s['max']:,.2f}",
                            "Count": s['count']
                        })
                    st.table(stats_list)
                else:
                    st.info("No numeric columns found in this file.")
            with tab2:
                data_q = st.text_input("Ask a question about the dataset:", placeholder="e.g. Which category has the highest sales?")
                if st.button("💡 Analyze Data") and data_q:
                    with st.spinner("Analyzing dataset with AI..."):
                        q_res = answer_tabular_question(df, data_q, preferred_model=st.session_state.preferred_model)
                        if q_res.get("success"):
                            st.markdown(q_res["content"])
                        else:
                            st.error(f"Error: {q_res.get('error')}")
            with tab3:
                st.markdown("##### Generate Visual Chart")
                col_x, col_y, col_type = st.columns(3)
                with col_x:
                    x_col = st.selectbox("X Axis (Category / Dimension)", options=df.columns)
                with col_y:
                    y_col = st.selectbox("Y Axis (Numeric Metric)", options=tab_data["numeric_columns"] or df.columns)
                with col_type:
                    c_type = st.selectbox("Chart Type", options=["bar", "line", "scatter"])
                
                if st.button("🎨 Render Chart", type="primary"):
                    chart_res = generate_data_chart(df, x_col, y_col, c_type)
                    if chart_res["success"]:
                        st.pyplot(chart_res["fig"])
                    else:
                        st.error(f"Chart error: {chart_res['error']}")

elif current_view == "docs":
    st.header("📝 Document Creator")
    st.caption("Generate downloadable PDF, Word (.docx), or Excel (.xlsx) reports on demand.")
    
    doc_format = st.radio("Choose Output Format:", options=["PDF (.pdf)", "Word (.docx)", "Excel (.xlsx)"], horizontal=True)
    doc_title = st.text_input("Document Title", value="Project Summary Report")
    
    if doc_format in ["PDF (.pdf)", "Word (.docx)"]:
        doc_content = st.text_area(
            "Document Body / Content (Markdown supported)",
            value="## Executive Summary\nThis document outlines our key project deliverables and strategic objectives.\n\n### Key Metrics\n- Target Completion: Q4\n- Efficiency Gain: +34%\n- Quality Standard: Verified",
            height=200
        )
        if st.button("🚀 Generate Document", type="primary"):
            if doc_format.startswith("PDF"):
                file_bytes = create_pdf_document(doc_title, doc_content)
                st.download_button("⬇️ Download PDF", data=file_bytes, file_name=f"{doc_title.lower().replace(' ', '_')}.pdf", mime="application/pdf")
            else:
                file_bytes = create_docx_document(doc_title, doc_content)
                st.download_button("⬇️ Download Word DOCX", data=file_bytes, file_name=f"{doc_title.lower().replace(' ', '_')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    else:
        st.markdown("##### Tabular Data Input")
        st.caption("Enter rows as comma-separated values (First line is header):")
        sample_csv_text = st.text_area("CSV Rows", value="Item,Quantity,Unit Price,Total\nLaptop,5,1200,6000\nMonitor,10,300,3000\nKeyboard,15,80,1200", height=150)
        if st.button("🚀 Generate Excel File", type="primary"):
            try:
                import io, pandas as pd
                temp_df = pd.read_csv(io.StringIO(sample_csv_text))
                excel_bytes = create_excel_document(doc_title, temp_df.to_dict('records'))
                st.download_button("⬇️ Download Excel XLSX", data=excel_bytes, file_name=f"{doc_title.lower().replace(' ', '_')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error(f"Error generating Excel file: {str(e)}")

elif current_view == "code":
    st.header("💻 Coding Assistant")
    st.caption("Generate, explain, and debug code across Python and popular programming languages.")
    
    code_mode = st.radio("Task Mode:", options=["✨ Generate Code", "📖 Explain Code", "🐞 Debug Error"], horizontal=True)
    lang = st.selectbox("Programming Language", options=["Python", "JavaScript", "TypeScript", "SQL", "HTML/CSS", "Go", "Rust", "C++", "Java"])
    
    if code_mode == "✨ Generate Code":
        req = st.text_area("Describe the requirements or feature to implement:", placeholder="e.g. Write a thread-safe LRU Cache in Python with get and put methods.")
        if st.button("🚀 Generate Code Solution", type="primary") and req:
            with st.spinner("Generating clean, idiomatic code..."):
                c_res = generate_code_solution(req, language=lang, preferred_model=st.session_state.preferred_model)
                if c_res.get("success"):
                    st.markdown(c_res["content"])
                else:
                    st.error(f"Error: {c_res.get('error')}")
    elif code_mode == "📖 Explain Code":
        code_input = st.text_area("Paste code snippet to explain:", height=200)
        if st.button("🔍 Explain Code", type="primary") and code_input:
            with st.spinner("Analyzing code architecture..."):
                e_res = explain_code_snippet(code_input, language=lang, preferred_model=st.session_state.preferred_model)
                if e_res.get("success"):
                    st.markdown(e_res["content"])
                else:
                    st.error(f"Error: {e_res.get('error')}")
    elif code_mode == "🐞 Debug Error":
        code_input = st.text_area("Buggy Code:", height=150)
        err_input = st.text_area("Error Traceback / Message:", height=100)
        if st.button("🔧 Debug Code", type="primary") and code_input:
            with st.spinner("Diagnosing root cause and synthesizing fix..."):
                d_res = debug_code_error(code_input, err_input, language=lang, preferred_model=st.session_state.preferred_model)
                if d_res.get("success"):
                    st.markdown(d_res["content"])
                else:
                    st.error(f"Error: {d_res.get('error')}")

elif current_view == "notes":
    st.header("📓 Smart Notes")
    st.caption("Create, edit, organize, and search persistent notes stored in your local SQLite database.")
    
    search_q = st.text_input("🔍 Search notes by title, content, or tag:", placeholder="Search keywords...")
    all_notes = get_all_notes(user_id=current_user_id, search_query=search_q)
    
    with st.expander("➕ Create New Note", expanded=len(all_notes) == 0):
        new_note_title = st.text_input("Note Title", placeholder="e.g. Architecture Decisions")
        new_note_tags = st.text_input("Tags (comma separated)", placeholder="e.g. dev, planning")
        new_note_body = st.text_area("Note Content (Markdown supported)", height=150)
        if st.button("💾 Save Note", type="primary") and new_note_title:
            create_note(title=new_note_title, content=new_note_body, tags=new_note_tags, user_id=current_user_id)
            st.success("Note saved successfully!")
            st.rerun()

    st.divider()
    st.markdown(f"##### Stored Notes ({len(all_notes)})")
    for n in all_notes:
        with st.container():
            col_t, col_act = st.columns([0.85, 0.15])
            with col_t:
                st.markdown(f"### {n['title']}")
                if n.get("tags"):
                    tags = [f"`{t.strip()}`" for t in n["tags"].split(",") if t.strip()]
                    st.markdown(" ".join(tags))
            with col_act:
                if st.button("🗑️", key=f"del_note_{n['id']}", help="Delete note"):
                    delete_note(n["id"], user_id=current_user_id)
                    st.rerun()
            st.markdown(n["content"])
            st.caption(f"Last updated: {n['updated_at']}")
            st.divider()

else:
    # Default: Autonomous Chat View
    current_id = st.session_state.current_session_id
    messages = get_session_messages(current_id, user_id=current_user_id)

    # Session Header Toolbar: Rename, Export TXT, Export MD
    sessions_lookup = {s["id"]: s for s in get_all_sessions(user_id=current_user_id)}
    current_session = sessions_lookup.get(current_id, {"title": "Chat"})

    with st.expander(f"⚙️ Conversation Options ({current_session.get('title', 'Chat')})", expanded=False):
        c_ren1, c_ren2 = st.columns([0.7, 0.3])
        with c_ren1:
            rename_val = st.text_input("Rename Chat Title", value=current_session.get("title", "New Chat"), key=f"rename_input_{current_id}")
        with c_ren2:
            st.write("")
            st.write("")
            if st.button("Save Title", key=f"btn_save_title_{current_id}") and rename_val.strip():
                update_session_title(current_id, rename_val.strip(), user_id=current_user_id)
                st.success("Renamed!")
                st.rerun()

        # Export features
        if messages:
            txt_lines = [f"=== Conversation: {current_session.get('title')} ===\n"]
            md_lines = [f"# Conversation: {current_session.get('title')}\n\n"]
            for m in messages:
                author = "User" if m["role"] == "user" else f"Assistant ({m.get('model_used', 'AI')})"
                txt_lines.append(f"[{m.get('timestamp')}] {author}:\n{m['content']}\n\n")
                md_lines.append(f"### {author}\n*{m.get('timestamp')}*\n\n{m['content']}\n\n---\n\n")

            txt_content = "".join(txt_lines)
            md_content = "".join(md_lines)
            safe_title = current_session.get('title', 'chat').lower().replace(' ', '_')[:30]

            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                st.download_button(
                    "📥 Export as Text (.txt)",
                    data=txt_content,
                    file_name=f"{safe_title}.txt",
                    mime="text/plain",
                    key=f"exp_txt_{current_id}"
                )
            with col_exp2:
                st.download_button(
                    "📥 Export as Markdown (.md)",
                    data=md_content,
                    file_name=f"{safe_title}.md",
                    mime="text/markdown",
                    key=f"exp_md_{current_id}"
                )

    # Render Chat History
    for msg in messages:
        role = msg["role"]
        avatar = "🧑‍💻" if role == "user" else "🌌"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])

            # Display Model Used & Sources for Assistant
            if role == "assistant":
                badges = []
                if msg.get("model_used"):
                    model_class = "badge-groq" if "groq" in msg["model_used"].lower() else "badge-gemini"
                    badges.append(f"<span class='status-pill {model_class}'>🤖 {msg['model_used']}</span>")

                if badges:
                    st.markdown("".join(badges), unsafe_allow_html=True)

                # Sources
                sources = msg.get("sources")
                if sources:
                    st.markdown("**Web Sources:**")
                    source_links = ""
                    for s in sources:
                        title = s.get("title", "Source")
                        url = s.get("url", "#")
                        source_links += f"<a class='source-tag' href='{url}' target='_blank'>🔗 {title}</a>"
                    st.markdown(source_links, unsafe_allow_html=True)

                # Agent Activities and Real-time Stages
                activities = msg.get("activities")
                tool_history = msg.get("tool_history")
                
                if activities or tool_history:
                    with st.expander("🔬 Autonomous Agent Execution Trace", expanded=False):
                        if activities:
                            st.markdown("##### 📌 Execution Pipeline")
                            stage_icons = {
                                "understanding": "🧠 Understanding Request",
                                "planning": "📋 Formulating Plan",
                                "selecting_tool": "🔧 Selecting Tool",
                                "executing_tool": "⚡ Executing Tool",
                                "analysing_results": "📊 Analysing Results",
                                "generating_answer": "✍️ Synthesizing Final Answer"
                            }
                            for act in activities:
                                stage_label = stage_icons.get(act.get("stage"), act.get("stage", "").title())
                                st.markdown(f"**{stage_label}**: {act.get('message', '')}")
                        
                        if tool_history:
                            st.markdown("##### 🛠️ Executed Tool Actions")
                            for idx, step in enumerate(tool_history, 1):
                                st.markdown(f"**Step {idx}: `{step.get('tool_name')}`**")
                                st.caption(f"Input Args: `{step.get('tool_args')}`")
                                st.markdown(f"> {step.get('result_summary')}")
                
                # Fallback to standard logs if no structured activities
                elif msg.get("agent_logs"):
                    with st.expander("🛠️ Agent Activity & Routing Trace", expanded=False):
                        for log_item in msg["agent_logs"]:
                            st.markdown(f"- `{log_item}`")

    # Chat Input & Execution
    if prompt := st.chat_input("Ask anything (e.g. 'What are today's top tech headlines?' or 'Explain quantum computing')"):
        # Display User message
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt)

        # Save User message to SQLite
        save_message(session_id=current_id, role="user", content=prompt, user_id=current_user_id)

        # Auto-rename session on first message
        if len(messages) == 0:
            new_title = truncate_text(prompt, max_chars=35)
            update_session_title(current_id, new_title, user_id=current_user_id)

        # Prepare chat history for agent
        formatted_history = [{"role": m["role"], "content": m["content"]} for m in messages]

        # Run Agent
        with st.chat_message("assistant", avatar="🌌"):
            with st.status("🧠 Autonomous Agent is planning & executing...", expanded=True) as status_box:
                status_box.write("1. Understanding user request & evaluating tools...")
                result = st.session_state.agent.run(
                    query=prompt,
                    chat_history=formatted_history,
                    preferred_model=st.session_state.preferred_model,
                    memory_enabled=st.session_state.memory_enabled,
                    user_id=current_user_id
                )
                # Display real stages completed
                if result.get("activities"):
                    for act in result["activities"]:
                        st.write(f"• **{act.get('stage', '').title()}**: {act.get('message')}")
                
                status_box.update(label="Complete! Response generated.", state="complete", expanded=False)

            # Inform user if model was switched due to fallback
            if result.get("model_switched") and result.get("switch_reason"):
                st.info(f"🔄 **Model Notice**: {result['switch_reason']}", icon="ℹ️")

            # Output the answer
            st.markdown(result["response"])

            # Show model badge
            if result.get("model_used"):
                model_class = "badge-groq" if "groq" in result["model_used"].lower() else "badge-gemini"
                st.markdown(f"<span class='status-pill {model_class}'>🤖 {result['model_used']}</span>", unsafe_allow_html=True)

            # Show sources
            sources = result.get("sources")
            if sources:
                st.markdown("**Web Sources:**")
                source_links = ""
                for s in sources:
                    title = s.get("title", "Source")
                    url = s.get("url", "#")
                    date_str = f" ({s.get('published_date')})" if s.get("published_date") else ""
                    source_links += f"<a class='source-tag' href='{url}' target='_blank'>🔗 {title}{date_str}</a>"
                st.markdown(source_links, unsafe_allow_html=True)

            # Agent activity trace expander
            activities = result.get("activities", [])
            tool_history = result.get("tool_history", [])
            if activities or tool_history:
                with st.expander("🔬 Autonomous Agent Execution Trace", expanded=False):
                    if activities:
                        st.markdown("##### 📌 Execution Pipeline")
                        stage_icons = {
                            "understanding": "🧠 Understanding Request",
                            "planning": "📋 Formulating Plan",
                            "selecting_tool": "🔧 Selecting Tool",
                            "executing_tool": "⚡ Executing Tool",
                            "analysing_results": "📊 Analysing Results",
                            "generating_answer": "✍️ Synthesizing Final Answer"
                        }
                        for act in activities:
                            stage_label = stage_icons.get(act.get("stage"), act.get("stage", "").title())
                            st.markdown(f"**{stage_label}**: {act.get('message', '')}")
                    
                    if tool_history:
                        st.markdown("##### 🛠️ Executed Tool Actions")
                        for idx, step in enumerate(tool_history, 1):
                            st.markdown(f"**Step {idx}: `{step.get('tool_name')}`**")
                            st.caption(f"Input Args: `{step.get('tool_args')}`")
                            st.markdown(f"> {step.get('result_summary')}")

            # Save assistant message to SQLite
            save_message(
                session_id=current_id,
                role="assistant",
                content=result["response"],
                model_used=result["model_used"],
                sources=sources,
                agent_logs=result.get("logs", []),
                activities=activities,
                tool_history=tool_history,
                user_id=current_user_id
            )

        # Rerun to update chat titles & state cleanly
        st.rerun()

