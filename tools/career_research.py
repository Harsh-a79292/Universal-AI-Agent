import json
from typing import Dict, Any, List, Optional
from tools.search import search_tavily
from models.llm_service import query_llm_with_fallback

def run_deep_research(topic: str, max_subqueries: int = 3, preferred_model: str = "auto") -> Dict[str, Any]:
    """
    Perform deep multi-query research using Tavily Search API.
    Deconstructs topic into subqueries, gathers sources, and synthesizes a structured report.
    """
    # 1. Break topic into focused search queries
    planning_prompt = f"""You are a Deep Research Lead.
The user wants to research the following topic in depth:
\"{topic}\"

Formulate {max_subqueries} distinct, highly focused search queries to explore this topic from multiple angles (e.g. background, state of the art, pros/cons, recent developments).

Respond strictly with a JSON list of strings, for example:
["query 1", "query 2", "query 3"]
"""
    plan_res = query_llm_with_fallback(planning_prompt, "Output valid JSON list of search query strings only.", preferred_model=preferred_model)
    
    subqueries = [topic]
    if plan_res.get("success"):
        try:
            content = plan_res["content"].strip()
            # extract json array
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                parsed = json.loads(content[start:end+1])
                if isinstance(parsed, list) and len(parsed) > 0:
                    subqueries = [str(q) for q in parsed[:max_subqueries]]
        except Exception:
            subqueries = [topic, f"{topic} latest developments", f"{topic} analysis"]
    
    # 2. Execute searches across subqueries
    all_sources = []
    collected_findings = []
    
    for q in subqueries:
        res = search_tavily(query=q, max_results=3)
        if res.get("success"):
            for item in res.get("results", []):
                if not any(s.get("url") == item.get("url") for s in all_sources):
                    all_sources.append(item)
                    collected_findings.append(f"Source [{item.get('title')}] ({item.get('url')}):\n{item.get('content')}")

    # 3. Synthesize comprehensive report
    findings_context = "\n\n".join(collected_findings[:10])
    synthesis_prompt = f"""Topic: {topic}

Verified Web Findings:
{findings_context}

Generate a comprehensive, professional Deep Research Report with the following structure:
1. Executive Summary
2. Key Insights & Critical Facts
3. In-Depth Analysis & Comparison
4. Verified Facts vs Unconfirmed Assumptions
5. Conclusion & Actionable Takeaways

Guidelines:
- Ground every single point in the verified web findings above.
- Never invent sources or URL citations.
- Mention publication dates if present.
"""
    system_instruction = "You are an elite research analyst. Ground all answers in provided web findings."
    report_res = query_llm_with_fallback(synthesis_prompt, system_instruction, preferred_model=preferred_model)
    
    return {
        "success": report_res.get("success", False),
        "topic": topic,
        "subqueries": subqueries,
        "sources": all_sources,
        "report": report_res.get("content", ""),
        "error": report_res.get("error")
    }

def research_job_opportunities(role: str, location: str = "", experience_level: str = "", preferred_model: str = "auto") -> Dict[str, Any]:
    """
    Search for actual job postings using Tavily and extract structured details.
    """
    query_parts = [role]
    if experience_level:
        query_parts.append(experience_level)
    if location:
        query_parts.append(f"in {location}")
    query_parts.append("job openings hiring 2025 2026")
    search_query = " ".join(query_parts)
    
    search_res = search_tavily(query=search_query, max_results=5)
    sources = search_res.get("results", [])
    
    if not sources:
        return {
            "success": False,
            "error": "No current job postings found for the specified criteria.",
            "jobs": [],
            "sources": []
        }
        
    context = ""
    for s in sources:
        context += f"Source URL: {s.get('url')}\nTitle: {s.get('title')}\nSnippet: {s.get('content')}\n\n"
        
    prompt = f"""Search Target: Role: {role}, Location: {location or 'Any'}, Level: {experience_level or 'Any'}

Web Search Results:
{context}

Extract all verified job openings from the search results.
For each listing, return:
- job_title
- company
- location (or 'Not specified')
- required_skills (list of skills)
- experience_required (or 'Not specified')
- source_url (must match original URL)
- verified_active: true or false (based strictly on whether the snippet states active hiring)

Do not fabricate company names or jobs. If information is missing, mark as 'Not specified'.

Respond ONLY with valid JSON in this schema:
[
  {{
    "job_title": "...",
    "company": "...",
    "location": "...",
    "required_skills": ["..."],
    "experience_required": "...",
    "source_url": "...",
    "verified_active": true
  }}
]
"""
    system_instruction = "You are a professional technical recruiter. Extract verified job facts only. Reply strictly in JSON."
    llm_res = query_llm_with_fallback(prompt, system_instruction, preferred_model=preferred_model)
    
    jobs = []
    if llm_res.get("success"):
        try:
            content = llm_res["content"].strip()
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                parsed = json.loads(content[start:end+1])
                if isinstance(parsed, list):
                    jobs = parsed
        except Exception:
            pass

    return {
        "success": True,
        "role": role,
        "location": location,
        "experience_level": experience_level,
        "jobs": jobs,
        "sources": sources,
        "error": None
    }

def analyze_skill_gap(current_skills: str, target_role: str, experience_level: str = "Mid-Level", preferred_model: str = "auto") -> Dict[str, Any]:
    """
    Analyze skill gap between user's current skills and market expectations for a target role.
    """
    prompt = f"""Target Role: {target_role}
Experience Level: {experience_level}
User-Provided Skills: {current_skills}

Instructions:
1. Identify all core and high-demand skills required for a {experience_level} {target_role} in the current market.
2. Clearly distinguish:
   - Skills the user already has (matched from user input)
   - Missing / Gap skills that must be learned
3. Provide a prioritized learning order (Critical, Recommended, Nice-to-have).
4. Propose 3 practical, portfolio-grade project suggestions to bridge the missing skills.
5. Highlight any user-provided skills that need deeper mastery vs completely new tools.
"""
    system_instruction = "You are a Principal Engineer and Career Mentor. Provide rigorous, candid skill gap breakdowns."
    return query_llm_with_fallback(prompt, system_instruction, preferred_model=preferred_model)

def generate_learning_roadmap(
    target_skill: str,
    target_duration_days: int = 30,
    daily_hours: float = 2.0,
    preferred_model: str = "auto"
) -> Dict[str, Any]:
    """
    Generate a granular daily and weekly learning roadmap with exercises and mini-projects.
    """
    total_hours = target_duration_days * daily_hours
    prompt = f"""Goal: Master or prepare for {target_skill}
Total Duration: {target_duration_days} Days
Available Study Time: {daily_hours} hours/day (Total ~{total_hours:.0f} hours)

Generate a structured, battle-tested learning curriculum:
1. Weekly Milestones & Theme breakdown.
2. Day-by-Day or Stage-by-Stage topic sequence.
3. Specific practical coding exercises for each phase.
4. Mini-project suggestions with architectural requirements.
5. Periodic Revision & Mock Interview / Knowledge Check schedules.
6. Progress Checkpoint criteria to verify mastery.
"""
    system_instruction = "You are a lead technical educator. Build structured, realistic daily study curriculums."
    return query_llm_with_fallback(prompt, system_instruction, preferred_model=preferred_model)

