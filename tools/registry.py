import json
from typing import Dict, Any, List
from tools.search import search_tavily
from tools.calculator import calculate_expression
from tools.datetime_tool import get_current_datetime
from tools.web_extractor import extract_website_content

# Tool definitions for Agent LLM reasoning
AVAILABLE_TOOLS_SPECS = [
    {
        "name": "web_search",
        "description": "Search the live web using Tavily for up-to-date facts, news, schedules, documentation, people, products, or current status. Supports multi-step comparative research.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Specific search query keywords."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to retrieve (1-5). Default is 4."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "calculator",
        "description": "Accurately and safely calculate mathematical expressions (e.g. arithmetic, percentages, powers, sqrt, logs, trigonometric operations). Never perform mental math for non-trivial formulas.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical formula to evaluate, e.g. '(1450 * 1.18) - 250' or 'sqrt(144) + 15'"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_datetime",
        "description": "Get current live date, time, day of the week, and timezone. Use whenever questions ask about 'today', 'now', 'current year/month', or relative timing.",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone_name": {
                    "type": "string",
                    "description": "Optional timezone name like 'UTC', 'America/New_York', or 'Asia/Kolkata'. Leave empty for system local."
                }
            }
        }
    },
    {
        "name": "extract_website",
        "description": "Fetch, clean, and extract readable text content from a specific public website URL found from search or provided by the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Valid public HTTP or HTTPS web page address."
                }
            },
            "required": ["url"]
        }
    }
]

def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely route and execute tool calls with argument validation.
    Prevents unauthorized system calls, booking/purchases, or external side effects.
    """
    # Safety Check: Disallow unauthorized side-effects
    disallowed_terms = ["booking", "purchase", "pay", "order", "delete_file", "bash", "terminal", "exec"]
    if any(term in tool_name.lower() for term in disallowed_terms):
        return {
            "success": False,
            "error": f"Safety constraint: The requested action '{tool_name}' requires external side-effects/financial transactions which are strictly prohibited in autonomous mode."
        }

    try:
        if tool_name == "web_search":
            query = tool_args.get("query", "").strip()
            if not query:
                return {"success": False, "error": "Missing required argument 'query' for web_search"}
            max_results = int(tool_args.get("max_results", 4))
            max_results = max(1, min(max_results, 6)) # bounds check
            return search_tavily(query=query, max_results=max_results)

        elif tool_name == "calculator":
            expression = str(tool_args.get("expression", "")).strip()
            if not expression:
                return {"success": False, "error": "Missing required argument 'expression' for calculator"}
            return calculate_expression(expression=expression)

        elif tool_name == "get_datetime":
            tz = tool_args.get("timezone_name")
            return get_current_datetime(timezone_name=tz)

        elif tool_name == "extract_website":
            url = str(tool_args.get("url", "")).strip()
            if not url:
                return {"success": False, "error": "Missing required argument 'url' for extract_website"}
            return extract_website_content(url=url)

        else:
            return {"success": False, "error": f"Unknown tool: '{tool_name}'"}

    except Exception as e:
        return {"success": False, "error": f"Error executing tool '{tool_name}': {str(e)}"}

