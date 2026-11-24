import json
import re
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from models.gemini_model import GeminiModel
from models.groq_model import GroqModel
from models.llm_service import query_llm_with_fallback
from tools.registry import AVAILABLE_TOOLS_SPECS, execute_tool
from config.settings import settings
from database.db import get_all_memories, create_memory

MAX_TOOL_STEPS = 5  # Safety boundary preventing infinite execution loops

class StepActivity(TypedDict):
    stage: str      # 'understanding', 'planning', 'selecting_tool', 'executing_tool', 'analysing_results', 'generating_answer'
    message: str
    details: Optional[Dict[str, Any]]

class AgentState(TypedDict):
    user_id: int
    user_query: str
    chat_history: List[Dict[str, str]]
    preferred_model: str  # "auto", "gemini", or "groq"
    memory_enabled: bool  # User preference flag
    active_memories: List[str]
    plan: str
    thought_steps: List[Dict[str, Any]]
    tool_history: List[Dict[str, Any]]
    step_count: int
    pending_tool_name: Optional[str]
    pending_tool_args: Optional[Dict[str, Any]]
    all_sources: List[Dict[str, Any]]
    final_response: str
    model_used: str
    model_switched: bool
    switch_reason: str
    activities: List[Dict[str, Any]]
    logs: List[str]

def parse_llm_json(content: str) -> Optional[Dict[str, Any]]:
    """Robustly parse JSON object from LLM response text."""
    try:
        # Try direct parse
        return json.loads(content)
    except Exception:
        pass

    # Extract ```json ``` or ``` ``` block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Find first { and last }
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(content[start:end+1])
        except Exception:
            pass
    return None

# --- LANGGRAPH NODES ---

def understand_and_plan_node(state: AgentState) -> AgentState:
    """Node 1: Understand user request, load relevant memories, and devise a plan."""
    activities = list(state.get("activities", []))
    logs = list(state.get("logs", []))
    query = state["user_query"]
    memory_enabled = state.get("memory_enabled", True)
    user_id = state.get("user_id", 1)

    # 1. Memory retrieval strictly scoped to authenticated user_id
    active_memories = []
    if memory_enabled:
        all_stored = get_all_memories(user_id=user_id, only_enabled=True)
        if all_stored:
            # Extract content of enabled memories
            active_memories = [m["content"] for m in all_stored]
            logs.append(f"🧠 Retrieved {len(active_memories)} active user memories/preferences.")

    # 2. Check if user explicitly shares a preference or fact to remember
    # e.g., "Remember that I prefer...", "My favorite language is...", "I live in..."
    pref_patterns = [
        r"remember that (.*)",
        r"remember (.*)",
        r"please note that (.*)",
        r"my favorite (.*) is (.*)",
        r"i prefer (.*)",
        r"i am allergic to (.*)",
        r"i live in (.*)"
    ]
    query_lower = query.lower().strip()
    if memory_enabled and any(re.search(pat, query_lower) for pat in pref_patterns):
        # Prevent sensitive info (passwords, keys)
        sensitive_terms = ["password", "secret", "api_key", "token", "credit_card", "ssn"]
        if not any(term in query_lower for term in sensitive_terms):
            extracted_fact = query.strip()
            # Clean leading command words
            for prefix in ["remember that ", "remember ", "please note that "]:
                if extracted_fact.lower().startswith(prefix):
                    extracted_fact = extracted_fact[len(prefix):].strip()
            if len(extracted_fact) > 3:
                create_memory(content=extracted_fact, category="preference", source="user", user_id=user_id)
                active_memories.append(extracted_fact)
                logs.append(f"💾 Saved new memory: '{extracted_fact}'")

    state["active_memories"] = active_memories

    activities.append({
        "stage": "understanding",
        "message": f"Analyzing user intent for: \"{query}\"",
        "details": {"query": query, "memory_count": len(active_memories)}
    })
    logs.append(f"🧠 Understanding request: '{query}'")

    tools_doc = json.dumps(AVAILABLE_TOOLS_SPECS, indent=2)

    planning_prompt = f"""You are the Planning Node of an Autonomous AI Agent.
Review the user's inquiry and the available tools below.

Available Tools:
{tools_doc}

User Query: "{query}"

Determine:
1. What does the user want to achieve?
2. Does this request require any tools, or can it be answered immediately from general knowledge (like greetings, explanations of concepts, writing code/poems)?
3. If tools are needed, outline the sequential actions (e.g. search specific keyword, compare findings, calculate numbers, extract page).

Respond ONLY with valid JSON in this schema:
{{
  "requires_tools": true or false,
  "plan": "Short summary of execution plan",
  "reasoning": "Why tools are or are not required"
}}
"""
    system_instruction = "You are a precise, logical autonomous planner. Output valid JSON only."
    llm_res = query_llm_with_fallback(planning_prompt, system_instruction, preferred_model=state.get("preferred_model", "auto"))

    requires_tools = False
    plan_desc = "Direct response reasoning"
    if llm_res.get("success"):
        parsed = parse_llm_json(llm_res["content"])
        if parsed and isinstance(parsed, dict):
            requires_tools = parsed.get("requires_tools", False)
            plan_desc = parsed.get("plan", "Standard response plan")
            logs.append(f"📋 Plan formulated: {plan_desc} (requires_tools: {requires_tools})")
        else:
            logs.append("ℹ️ Planning JSON parse fallback, using default reasoning.")
    else:
        logs.append(f"⚠️ Planner error: {llm_res.get('error')}")

    activities.append({
        "stage": "planning",
        "message": f"Plan: {plan_desc}",
        "details": {"requires_tools": requires_tools, "plan": plan_desc}
    })

    state["plan"] = plan_desc
    state["activities"] = activities
    state["logs"] = logs
    if not state.get("model_used") and llm_res.get("model"):
        state["model_used"] = llm_res["model"]
    if llm_res.get("model_switched"):
        state["model_switched"] = True
        state["switch_reason"] = llm_res.get("switch_reason", "")

    return state

def reason_and_decide_tool_node(state: AgentState) -> AgentState:
    """
    Node 2: ReAct Decider.
    Analyses past tool execution history and decides either to call another tool or finish.
    """
    activities = list(state.get("activities", []))
    logs = list(state.get("logs", []))
    query = state["user_query"]
    tool_history = state.get("tool_history", [])
    step_count = state.get("step_count", 0)

    # Safety step limit check
    if step_count >= MAX_TOOL_STEPS:
        logs.append(f"🛑 Maximum tool steps ({MAX_TOOL_STEPS}) reached. Forcing response synthesis.")
        state["pending_tool_name"] = None
        state["pending_tool_args"] = None
        return state

    history_summary = ""
    if tool_history:
        history_summary = "Previous Tool Steps Taken:\n"
        for i, step in enumerate(tool_history, 1):
            history_summary += (
                f"Step {i}:\n"
                f"  Tool: {step.get('tool_name')}\n"
                f"  Arguments: {json.dumps(step.get('tool_args'))}\n"
                f"  Result Summary: {step.get('result_summary')}\n"
            )

    tools_doc = json.dumps(AVAILABLE_TOOLS_SPECS, indent=2)

    prompt = f"""You are the Tool Decision Engine of an Autonomous ReAct Agent.
User Query: "{query}"
Current Plan: "{state.get('plan')}"

Available Tools:
{tools_doc}

{history_summary}

Based on the user inquiry and any previous tool results:
- If you have gathered sufficient information to provide a comprehensive, truthful answer, select action "FINISH".
- If you still need more information (e.g. a second search query to compare sources, a web page extraction for deep details, a calculation of verified numbers, or date/time), select action "CALL_TOOL".

Respond ONLY with a JSON object in this schema:
{{
  "action": "CALL_TOOL" or "FINISH",
  "thought": "Your internal thought on what is missing or if we are ready",
  "tool_name": "web_search" | "calculator" | "get_datetime" | "extract_website" | null,
  "tool_args": {{ ... }} | null
}}
"""
    system_instruction = "You are an autonomous ReAct decision engine. Select appropriate tools or finish. Reply strictly in JSON."
    llm_res = query_llm_with_fallback(prompt, system_instruction, preferred_model=state.get("preferred_model", "auto"))

    action = "FINISH"
    tool_name = None
    tool_args = None
    thought = "Ready to respond"

    if llm_res.get("success"):
        parsed = parse_llm_json(llm_res["content"])
        if parsed and isinstance(parsed, dict):
            action = parsed.get("action", "FINISH")
            thought = parsed.get("thought", "")
            tool_name = parsed.get("tool_name")
            tool_args = parsed.get("tool_args") or {}

            # Sanity check: tool exists in registry
            valid_names = [t["name"] for t in AVAILABLE_TOOLS_SPECS]
            if action == "CALL_TOOL" and tool_name not in valid_names:
                logs.append(f"⚠️ Model proposed invalid tool '{tool_name}'. Defaulting to finish.")
                action = "FINISH"
                tool_name = None

    if action == "CALL_TOOL" and tool_name:
        activities.append({
            "stage": "selecting_tool",
            "message": f"Selected tool '{tool_name}' (Step {step_count + 1})",
            "details": {"tool_name": tool_name, "tool_args": tool_args, "thought": thought}
        })
        logs.append(f"🔧 Tool selected: '{tool_name}' with args {json.dumps(tool_args)}")
        state["pending_tool_name"] = tool_name
        state["pending_tool_args"] = tool_args
    else:
        logs.append("🎯 Sufficient information gathered or direct answer path selected.")
        state["pending_tool_name"] = None
        state["pending_tool_args"] = None

    state["activities"] = activities
    state["logs"] = logs
    if not state.get("model_used") and llm_res.get("model"):
        state["model_used"] = llm_res["model"]
    if llm_res.get("model_switched"):
        state["model_switched"] = True
        state["switch_reason"] = llm_res.get("switch_reason", "")

    return state

def execute_tool_node(state: AgentState) -> AgentState:
    """Node 3: Execute the selected tool and capture result."""
    activities = list(state.get("activities", []))
    logs = list(state.get("logs", []))
    tool_history = list(state.get("tool_history", []))
    all_sources = list(state.get("all_sources", []))

    tool_name = state.get("pending_tool_name")
    tool_args = state.get("pending_tool_args") or {}

    activities.append({
        "stage": "executing_tool",
        "message": f"Executing '{tool_name}'...",
        "details": {"tool_name": tool_name, "tool_args": tool_args}
    })
    logs.append(f"⚡ Executing tool: '{tool_name}'...")

    # Run tool safely
    raw_result = execute_tool(tool_name, tool_args)

    # Format result summary for LLM context
    result_summary = ""
    if tool_name == "web_search":
        if raw_result.get("success"):
            results = raw_result.get("results", [])
            for r in results:
                # Add unique sources
                if not any(s.get("url") == r.get("url") for s in all_sources):
                    all_sources.append(r)
            result_summary = f"Found {len(results)} search results. Snippets: " + "; ".join(
                [f"[{r.get('title')}] (Date: {r.get('published_date') or 'N/A'}): {r.get('content')[:150]}" for r in results[:4]]
            )
            logs.append(f"✅ Web search completed with {len(results)} items.")
        else:
            result_summary = f"Search error: {raw_result.get('error')}"
            logs.append(f"⚠️ Web search error: {raw_result.get('error')}")

    elif tool_name == "calculator":
        if raw_result.get("success"):
            result_summary = f"Formula: {raw_result.get('expression')} = {raw_result.get('result')}"
            logs.append(f"✅ Calculation successful: {result_summary}")
        else:
            result_summary = f"Calculation error: {raw_result.get('error')}"
            logs.append(f"⚠️ Calculation error: {raw_result.get('error')}")

    elif tool_name == "get_datetime":
        if raw_result.get("success"):
            result_summary = f"Current timestamp: {raw_result.get('formatted')}"
            logs.append(f"✅ Datetime retrieved: {raw_result.get('formatted')}")
        else:
            result_summary = f"Datetime error: {raw_result.get('error')}"

    elif tool_name == "extract_website":
        if raw_result.get("success"):
            result_summary = f"Extracted from {raw_result.get('url')} (Title: {raw_result.get('title')}): {raw_result.get('content')[:500]}"
            logs.append(f"✅ Webpage extracted ({raw_result.get('char_count')} chars).")
            # Also record page as source if not already present
            if not any(s.get("url") == raw_result.get("url") for s in all_sources):
                all_sources.append({
                    "title": raw_result.get("title") or raw_result.get("url"),
                    "url": raw_result.get("url"),
                    "content": raw_result.get("content")[:300],
                    "published_date": None
                })
        else:
            result_summary = f"Extraction error: {raw_result.get('error')}"
            logs.append(f"⚠️ Webpage extraction error: {raw_result.get('error')}")

    # Record step
    tool_history.append({
        "tool_name": tool_name,
        "tool_args": tool_args,
        "raw_result": raw_result,
        "result_summary": result_summary
    })

    # Node: Analysing results activity
    activities.append({
        "stage": "analysing_results",
        "message": f"Analyzing results from '{tool_name}'",
        "details": {"summary": result_summary[:200]}
    })

    state["tool_history"] = tool_history
    state["all_sources"] = all_sources
    state["step_count"] = state.get("step_count", 0) + 1
    state["pending_tool_name"] = None
    state["pending_tool_args"] = None
    state["activities"] = activities
    state["logs"] = logs

    return state

def generate_final_answer_node(state: AgentState) -> AgentState:
    """Node 4: Synthesize final comprehensive response citing sources and facts."""
    activities = list(state.get("activities", []))
    logs = list(state.get("logs", []))
    query = state["user_query"]
    tool_history = state.get("tool_history", [])

    activities.append({
        "stage": "generating_answer",
        "message": "Generating final response with verified findings and citations...",
        "details": {}
    })
    logs.append("✍️ Synthesizing final answer...")

    context_blocks = []
    if tool_history:
        context_blocks.append("--- RESEARCH AND TOOL EXECUTION LOGS ---")
        for i, step in enumerate(tool_history, 1):
            context_blocks.append(f"Step {i} ({step.get('tool_name')}): {step.get('result_summary')}")
        context_blocks.append("----------------------------------------")

    history_str = ""
    if state.get("chat_history"):
        history_str = "Conversation Context:\n"
        for msg in state["chat_history"][-3:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_str += f"{role}: {msg['content']}\n"
        history_str += "\n"

    memory_str = ""
    active_mems = state.get("active_memories", [])
    if active_mems:
        memory_str = "Known User Preferences and Long-Term Memories:\n"
        for mem in active_mems:
            memory_str += f"- {mem}\n"
        memory_str += "\n"

    system_instruction = (
        "You are an Autonomous Universal AI Agent. Provide accurate, well-structured, objective, and clear answers. "
        "Guidelines:\n"
        "1. Honor any known user preferences or memories provided in the context.\n"
        "2. If tool findings are provided, ground your answer strictly in the verified facts and compare findings across steps.\n"
        "3. Clearly distinguish between verified facts and missing/unconfirmed information.\n"
        "4. When referencing web sources, mention their publication dates if available.\n"
        "5. Never hallucinate calculations: use the exact calculated results from the tools.\n"
        "6. Never make assumptions about flight/hotel bookings or financial purchases.\n"
        "7. Use GitHub-flavored markdown with bullet points, bold headings, and clean tables where appropriate."
    )

    prompt = f"""{memory_str}{history_str}
{chr(10).join(context_blocks)}

User Question: {query}

Provide a comprehensive and helpful response based on the above findings:"""

    llm_res = query_llm_with_fallback(prompt, system_instruction, preferred_model=state.get("preferred_model", "auto"))

    if llm_res.get("success"):
        state["final_response"] = llm_res["content"]
        state["model_used"] = llm_res["model"]
        logs.append(f"✅ Final response generated via {llm_res['model']}")
    else:
        state["final_response"] = (
            f"An error occurred while generating the final response: {llm_res.get('error')}. "
            "Please verify your API keys and try again."
        )
        state["model_used"] = "None"
        logs.append(f"❌ LLM error: {llm_res.get('error')}")

    if llm_res.get("model_switched"):
        state["model_switched"] = True
        state["switch_reason"] = llm_res.get("switch_reason", "")

    state["activities"] = activities
    state["logs"] = logs
    return state

# --- GRAPH BUILDER ---

def create_autonomous_agent_graph():
    """Build the autonomous ReAct graph in LangGraph."""
    graph = StateGraph(AgentState)

    graph.add_node("understand_and_plan", understand_and_plan_node)
    graph.add_node("reason_and_decide", reason_and_decide_tool_node)
    graph.add_node("execute_tool", execute_tool_node)
    graph.add_node("generate_answer", generate_final_answer_node)

    graph.set_entry_point("understand_and_plan")

    graph.add_edge("understand_and_plan", "reason_and_decide")

    def route_after_decision(state: AgentState):
        if state.get("pending_tool_name"):
            return "execute_tool"
        return "generate_answer"

    graph.add_conditional_edges(
        "reason_and_decide",
        route_after_decision,
        {
            "execute_tool": "execute_tool",
            "generate_answer": "generate_answer"
        }
    )

    # After tool execution, loop back to ReAct reasoner to decide if another tool is needed
    graph.add_edge("execute_tool", "reason_and_decide")
    graph.add_edge("generate_answer", END)

    return graph.compile()

class UniversalAgent:
    def __init__(self):
        self.app = create_autonomous_agent_graph()

    def run(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        preferred_model: str = "auto",
        memory_enabled: bool = True,
        user_id: int = 1
    ) -> Dict[str, Any]:
        initial_state: AgentState = {
            "user_id": user_id,
            "user_query": query,
            "chat_history": chat_history or [],
            "preferred_model": preferred_model,
            "memory_enabled": memory_enabled,
            "active_memories": [],
            "plan": "",
            "thought_steps": [],
            "tool_history": [],
            "step_count": 0,
            "pending_tool_name": None,
            "pending_tool_args": None,
            "all_sources": [],
            "final_response": "",
            "model_used": "",
            "model_switched": False,
            "switch_reason": "",
            "activities": [],
            "logs": []
        }

        output_state = self.app.invoke(initial_state)

        return {
            "response": output_state.get("final_response", ""),
            "model_used": output_state.get("model_used", ""),
            "model_switched": output_state.get("model_switched", False),
            "switch_reason": output_state.get("switch_reason", ""),
            "sources": output_state.get("all_sources", []),
            "activities": output_state.get("activities", []),
            "tool_history": output_state.get("tool_history", []),
            "logs": output_state.get("logs", []),
            "active_memories": output_state.get("active_memories", [])
        }
