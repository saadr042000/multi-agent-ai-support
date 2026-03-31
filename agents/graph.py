"""
LangGraph Multi-Agent Orchestration
====================================
Graph structure:
  supervisor ─→ sql_agent  ─┐
             ─→ rag_agent  ─┼─→ synthesizer → END
             ─→ both_agent ─┘
             ─→ synthesizer (for general queries)

The supervisor classifies each query, routes it, each agent fetches
context, and the synthesizer produces the final user-facing response.
"""
from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict

import anthropic
from langgraph.graph import END, StateGraph

from config import ANTHROPIC_API_KEY, MODEL
from tools.sql_tools import nl_to_sql_and_run
from tools.rag_tools import search_documents

# ── State definition ──────────────────────────────────────────────────────────

class AgentState(TypedDict):
    query: str
    query_type: Optional[str]          # sql | rag | both | general
    sql_data: Optional[dict]           # {"sql": ..., "raw_results": ...}
    rag_data: Optional[str]            # retrieved passages
    final_response: str
    chat_history: list[dict]           # [{"role": ..., "content": ...}]
    agent_trace: Annotated[list, operator.add]  # for UI transparency


# ── Shared Claude client ───────────────────────────────────────────────────────

def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ── Node functions ─────────────────────────────────────────────────────────────

def supervisor_node(state: AgentState) -> AgentState:
    """Classifies the query and sets query_type for routing."""
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=10,
        system="""You are a query router for a customer-support AI system.
Classify the user query into exactly ONE of these categories:
  sql     – needs structured customer/ticket data from the database
  rag     – needs information from uploaded policy/procedure documents
  both    – needs BOTH database data AND policy documents
  general – a general conversational question; no specific data needed

Respond with ONLY the category word, nothing else.""",
        messages=[{"role": "user", "content": state["query"]}],
    )

    raw = resp.content[0].text.strip().lower()
    query_type = raw if raw in {"sql", "rag", "both", "general"} else "general"
    return {
        **state,
        "query_type": query_type,
        "agent_trace": [f"🧭 Supervisor → routed to **{query_type}** agent"],
    }


def sql_agent_node(state: AgentState) -> AgentState:
    """Queries the SQLite database with natural language."""
    try:
        result = nl_to_sql_and_run(state["query"])
        trace = [f"📊 SQL Agent → `{result['sql']}`"]
    except Exception as e:
        result = {"sql": "error", "raw_results": f"SQL agent error: {e}"}
        trace = [f"📊 SQL Agent → error: {e}"]
    return {**state, "sql_data": result, "agent_trace": trace}


def rag_agent_node(state: AgentState) -> AgentState:
    """Searches the vector DB for relevant policy content."""
    result = search_documents(state["query"])
    trace = ["📄 RAG Agent → retrieved policy passages"]
    return {**state, "rag_data": result, "agent_trace": trace}


def both_agent_node(state: AgentState) -> AgentState:
    """Runs both SQL and RAG agents sequentially."""
    state = sql_agent_node(state)
    state = rag_agent_node(state)
    return state


def synthesizer_node(state: AgentState) -> AgentState:
    """Produces the final natural-language response for the user."""
    context_blocks: list[str] = []

    if state.get("sql_data"):
        d = state["sql_data"]
        context_blocks.append(
            f"=== Structured Customer Data ===\n"
            f"SQL used: {d.get('sql', '')}\n"
            f"Results:\n{d.get('raw_results', 'No data')}"
        )

    if state.get("rag_data"):
        rag = state["rag_data"]
        if not rag.startswith("NO_DOCUMENTS"):
            context_blocks.append(
                f"=== Policy / Document Knowledge Base ===\n{rag}"
            )
        else:
            context_blocks.append(rag)

    context = "\n\n".join(context_blocks) if context_blocks else ""

    user_msg = state["query"]
    if context:
        user_msg = f"User question: {state['query']}\n\nRelevant context:\n{context}"

    history = state.get("chat_history", [])
    messages = history + [{"role": "user", "content": user_msg}]

    resp = _client().messages.create(
        model=MODEL,
        max_tokens=1024,
        system="""You are a knowledgeable, professional customer support assistant helping John (a support executive).

Guidelines:
- Use the provided context to give accurate, specific answers.
- Format your responses with clear structure (bold headings, bullet points) when showing data.
- If showing customer data, present it in a readable, organized way.
- If context says NO_DOCUMENTS, politely mention that no policy documents have been uploaded yet.
- If context is empty, answer from general knowledge and note the limitation.
- Be concise but complete. Proactively highlight important details.
""",
        messages=messages,
    )

    final = resp.content[0].text
    return {
        **state,
        "final_response": final,
        "agent_trace": ["✅ Synthesizer → response generated"],
    }


# ── Routing helpers ────────────────────────────────────────────────────────────

def route_supervisor(state: AgentState) -> str:
    return state["query_type"]


# ── Graph construction ─────────────────────────────────────────────────────────

def create_graph():
    wf = StateGraph(AgentState)

    wf.add_node("supervisor",   supervisor_node)
    wf.add_node("sql_agent",    sql_agent_node)
    wf.add_node("rag_agent",    rag_agent_node)
    wf.add_node("both_agent",   both_agent_node)
    wf.add_node("synthesizer",  synthesizer_node)

    wf.set_entry_point("supervisor")

    wf.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "sql":     "sql_agent",
            "rag":     "rag_agent",
            "both":    "both_agent",
            "general": "synthesizer",
        },
    )

    for node in ("sql_agent", "rag_agent", "both_agent"):
        wf.add_edge(node, "synthesizer")

    wf.add_edge("synthesizer", END)

    return wf.compile()
