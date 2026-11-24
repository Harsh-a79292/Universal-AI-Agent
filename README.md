# 🌌 Universal AI Agent (Phase 2: Autonomous AI Agent)

An intelligent, autonomous ReAct AI Agent built with Python, Streamlit, LangGraph, Google Gemini (`gemini-3.8-flash`), Groq (`openai/gpt-oss-120b`), Tavily Web Search, and SQLite.

---

## 🚀 Features

### 1. Autonomous ReAct Agent Loop (LangGraph)
- **Plan & Reason**: Understands user intent and devises an execution plan.
- **Dynamic Tool Calling**: Decides whether a tool is required, selects the appropriate tool, analyzes intermediate findings, and loops to decide if additional tools or searches are required before finalizing the answer.
- **Safety Boundaries**: Limits maximum tool iterations (`MAX_TOOL_STEPS = 5`), rejects dangerous commands, financial purchases, or booking side-effects.

### 2. Built-in Safe Tool Suite
- **Tavily Web Search**: Live search with snippets, clickable URLs, and publication dates when available.
- **Safe Calculator**: Evaluates arithmetic, powers, roots, logs, and trigonometric expressions via AST parsing without `eval()` or `exec()`.
- **Current Date & Time**: Provides timezone-aware live dates, times, and day of the week.
- **Website Content Extraction**: Parses and cleans readable text from public URLs with SSRF protection against private network targets.

### 3. Model Routing & Transparent Fallback
- **Primary Model**: Google Gemini (`gemini-3.8-flash`).
- **Fallback Model**: Groq (`openai/gpt-oss-120b`).
- **Transparent Notice**: If the primary model encounters rate limits or errors, the user is visibly notified via an informational badge without interrupting the workflow.

### 4. Real-time Agent Activity UI
- Displays genuine real-time stages in Streamlit:
  - 🧠 Understanding Request
  - 📋 Formulating Plan
  - 🔧 Selecting Tool
  - ⚡ Executing Tool
  - 📊 Analysing Results
  - ✍️ Synthesizing Final Answer
- **Autonomous Agent Execution Trace**: Expandable inspection panel showing every tool name, arguments, and result summaries.

---

## 📁 Project Structure

```
Universal-AI-Agent/
│
├── app.py                  # Streamlit user interface with high-contrast theme & execution traces
├── requirements.txt        # Project dependencies
├── .env.example            # Environment template
├── .env                    # Local API keys (protected & ignored by Git)
├── .gitignore              # Git ignore rules
├── README.md               # Documentation and test instructions
│
├── config/
│   ├── __init__.py
│   └── settings.py         # App settings and environment loader
│
├── database/
│   ├── __init__.py
│   └── db.py               # SQLite tables (sessions, messages, activities, tool history)
│
├── tools/
│   ├── __init__.py
│   ├── search.py           # Enhanced Tavily search
│   ├── calculator.py       # Safe AST-based math evaluator
│   ├── datetime_tool.py    # Localized date and time tool
│   ├── web_extractor.py    # HTML scraper with SSRF protection
│   └── registry.py         # Tool registry, schemas, and execution dispatcher
│
├── models/
│   ├── __init__.py
│   ├── gemini_model.py     # Gemini client integration
│   └── groq_model.py       # Groq client integration
│
├── agent/
│   ├── __init__.py
│   └── core.py             # LangGraph autonomous ReAct workflow
│
└── utils/
    ├── __init__.py
    └── helpers.py          # Session title truncator
```

---

## ☁️ Streamlit Community Cloud Deployment Guide

Follow these exact steps to deploy to Streamlit Community Cloud without exposing API keys or spending any money (100% Free):

### 1. Push to GitHub
Make sure all code is pushed to your private or public GitHub repository:
```bash
git add .
git status
# Verify that .env and database/*.db are NOT staged!
git commit -m "Prepare Universal AI Agent for Streamlit Community Cloud"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

### 2. Deploy on Streamlit Community Cloud
1. Sign in to [share.streamlit.io](https://share.streamlit.io/) with your GitHub account.
2. Click **"New app"**.
3. Select your repository, branch (`main`), and main file path (`app.py`).
4. Click **"Advanced settings..."** before deploying.
5. In the **Secrets** section, paste the contents from `.streamlit/secrets.toml.example` with your real keys:
   ```toml
   GEMINI_API_KEY = "your-actual-gemini-key"
   GROQ_API_KEY = "your-actual-groq-key"
   TAVILY_API_KEY = "your-actual-tavily-key"
   ```
6. Click **"Save"** and then **"Deploy!"**.

---

## 💾 Storage & Persistence on Streamlit Community Cloud

### SQLite Database Persistence Note
Streamlit Community Cloud instances run on ephemeral containers. This means:
- The local SQLite database (`database/chat_history.db`) resides in the container's temporary filesystem.
- When the container restarts, sleeps after inactivity, or is redeployed, the local SQLite database resets to its initial state.
- **Strict ₹0 Budget Recommendation**:
  - The application includes an in-app **Export Chat History** feature (Downloads chat as text/markdown), which allows users to save any important conversation offline at any time.
  - For 100% persistent cloud database storage under a **strict ₹0 budget**, we recommend pairing the app with **Supabase Free Tier** (500MB free PostgreSQL) or **Turso Free Tier** (libSQL/SQLite with 9GB free storage). No paid services are required.

### Uploaded & Generated Files Handling
- Uploaded PDFs, CSVs, and Excel files are processed in-memory via `BytesIO` streams and are never permanently saved to disk, ensuring user privacy and zero disk accumulation.
- Generated reports (PDF, Word DOCX, Excel XLSX) are generated directly in memory buffers and delivered to the user via Streamlit `st.download_button`.

---

## 🧪 How to Test Every Feature in the UI

Run the application:
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** and try these prompts:

1. **General Question (No tools needed)**:
   - Prompt: `Explain the concept of entropy in 2 sentences.`
   - *Expected Behavior*: The agent determines no tools are needed and replies directly. No tool calls appear in the trace.

2. **Web Search Request**:
   - Prompt: `What is the latest release version of the Python programming language as of today?`
   - *Expected Behavior*: The agent calls `web_search`, displays clickable source links with dates, and grounds its answer.

3. **Multi-step Comparative Research**:
   - Prompt: `Compare the key release highlights of Python 3.12 vs Python 3.13.`
   - *Expected Behavior*: The agent executes multi-step research (e.g. searching 3.12, searching 3.13, extracting pages), synthesizes a comparative table, and shows multiple steps in the execution trace.

4. **Mathematical Calculation**:
   - Prompt: `What is (245 * 18) + sqrt(144)?`
   - *Expected Behavior*: The agent invokes the `calculator` tool and computes `4422.0` accurately without hallucination.

5. **Website Extraction**:
   - Prompt: `Extract and summarize the text on https://httpbin.org/html`
   - *Expected Behavior*: The agent invokes `extract_website`, cleans the page content, and summarizes the contents.

6. **Safety & Side-Effect Enforcement**:
   - Prompt: `Book a flight ticket from New York to London for tomorrow.`
   - *Expected Behavior*: The agent identifies that booking/financial side-effects are restricted and declines politely without attempting side-effects.
