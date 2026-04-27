"""
LangGraph Agentic Workflow — Researcher Query Agent
=====================================================
Implements a multi-step ReAct-style agent using LangGraph that:
  1. Classifies the user's intent (search / compare / profile / recommend)
  2. Routes to the right tool (semantic_search, researcher_profile, cluster_info)
  3. Synthesises a grounded final answer with citations

Graph topology:
    START → classify_intent → [tool_node] → synthesise → END

Tools available to the agent
─────────────────────────────
• semantic_search   – FAISS nearest-neighbour search over 52k papers
• researcher_profile – full profile for a named researcher
• cluster_overview  – summary of a domain cluster
"""

from __future__ import annotations

import json
import logging
import os
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)

# ── lazy imports to avoid circular dependency ──────────────────────────────────
_rag_pipeline = None
_clustering_engine = None


def _get_rag():
    global _rag_pipeline
    return _rag_pipeline


def _get_ce():
    global _clustering_engine
    return _clustering_engine


def init_agent_dependencies(rag_pipeline, clustering_engine):
    """Called from main.py lifespan after both engines are ready."""
    global _rag_pipeline, _clustering_engine
    _rag_pipeline = rag_pipeline
    _clustering_engine = clustering_engine
    logger.info("Agent dependencies initialised.")


# ── Tool definitions ──────────────────────────────────────────────────────────

@tool
def semantic_search(query: str, top_k: int = 5) -> str:
    """
    Search the academic paper database using semantic similarity.
    Returns the top matching papers with author, year, citations, and domain.
    Use this for questions about papers, topics, or research areas.
    """
    rag = _get_rag()
    if rag is None:
        return json.dumps({"error": "RAG pipeline not ready"})
    results = rag.search(query, top_k=top_k)
    return json.dumps(results[:top_k], default=str)


@tool
def researcher_profile(name: str) -> str:
    """
    Retrieve the full profile of a specific researcher by name.
    Returns their publications, h-index, total citations, research interests,
    and domain cluster. Use this when the user asks about a specific person.
    """
    ce = _get_ce()
    if ce is None:
        return json.dumps({"error": "Clustering engine not ready"})
    profile = ce.get_researcher_profile(name)
    if not profile:
        return json.dumps({"error": f"Researcher '{name}' not found"})
    return json.dumps(profile, default=str)


@tool
def cluster_overview(cluster_name: str) -> str:
    """
    Get a summary of a research domain cluster: top researchers, paper count,
    and representative topics. Valid clusters: Machine Learning & AI,
    Cryptography & Security, Algorithms & Theory, Distributed & Systems,
    Bioinformatics & Computational Biology, Database & Information Retrieval,
    Programming Languages & Software, Human-Computer Interaction, Robotics &
    Computer Vision, Quantum Computing.
    """
    ce = _get_ce()
    if ce is None:
        return json.dumps({"error": "Clustering engine not ready"})
    clusters = ce.get_clusters()
    match = next(
        (c for c in clusters if cluster_name.lower() in c.get("name", "").lower()),
        None,
    )
    if not match:
        return json.dumps({"error": f"Cluster '{cluster_name}' not found", "available": [c["name"] for c in clusters]})
    return json.dumps(match, default=str)


# ── Agent state ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: Optional[str]
    tool_results: list[dict]
    final_answer: Optional[str]


# ── LLM + tools ───────────────────────────────────────────────────────────────

TOOLS = [semantic_search, researcher_profile, cluster_overview]
TOOL_MAP = {t.name: t for t in TOOLS}

SYSTEM_PROMPT = """You are an expert academic research assistant for the AI Researcher Profiling Platform.
You have access to a database of 317 researchers and 52,000+ publications.

You have three tools:
1. semantic_search — find relevant papers by topic/keyword
2. researcher_profile — get full profile of a specific researcher by name
3. cluster_overview — get a summary of a research domain cluster

Rules:
- Always use at least one tool before answering
- For questions about a specific researcher, always use researcher_profile
- For topic/paper questions, use semantic_search
- For domain overview questions, use cluster_overview
- Cite paper titles and authors in your final answer
- If you cannot find relevant results, say so honestly
- Be concise and specific"""


def _build_llm():
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        api_key=api_key,
    ).bind_tools(TOOLS)


# ── Graph nodes ───────────────────────────────────────────────────────────────

def agent_node(state: AgentState) -> dict:
    """Central agent node: decides which tool to call (or finishes)."""
    llm = _build_llm()
    if llm is None:
        # Fallback: no LLM key — run semantic_search directly
        query = state["messages"][-1].content if state["messages"] else ""
        result = semantic_search.invoke({"query": query, "top_k": 5})
        return {
            "messages": [AIMessage(content=f"[No-LLM mode] Top results:\n{result}")],
            "final_answer": result,
        }

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def tool_node(state: AgentState) -> dict:
    """Execute whatever tool the agent requested."""
    last = state["messages"][-1]
    tool_messages = []
    tool_results = list(state.get("tool_results", []))

    for tool_call in last.tool_calls:
        fn = TOOL_MAP.get(tool_call["name"])
        if fn is None:
            result = json.dumps({"error": f"Unknown tool: {tool_call['name']}"})
        else:
            try:
                result = fn.invoke(tool_call["args"])
            except Exception as exc:
                result = json.dumps({"error": str(exc)})

        tool_results.append({"tool": tool_call["name"], "args": tool_call["args"], "result": result})
        tool_messages.append(
            ToolMessage(content=result, tool_call_id=tool_call["id"])
        )

    return {"messages": tool_messages, "tool_results": tool_results}


def should_continue(state: AgentState) -> str:
    """Route: call another tool, or finish."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return END


# ── Graph construction ────────────────────────────────────────────────────────

def build_agent_graph() -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")   # always return to agent after tool use

    return graph.compile()


# Module-level compiled graph (initialised once)
agent_graph = build_agent_graph()


# ── Public API ────────────────────────────────────────────────────────────────

def run_agent(query: str, chat_history: list[dict] | None = None) -> dict:
    """
    Run the LangGraph agent for a user query.
    Returns: { answer, tool_calls, sources }
    """
    messages = []
    for turn in (chat_history or [])[-4:]:
        cls = HumanMessage if turn.get("role") == "user" else AIMessage
        messages.append(cls(content=turn["content"]))
    messages.append(HumanMessage(content=query))

    try:
        result = agent_graph.invoke(
            {"messages": messages, "tool_results": []},
            config={"recursion_limit": 8},
        )
    except Exception as exc:
        logger.error(f"Agent error: {exc}")
        return {"answer": f"Agent error: {exc}", "tool_calls": [], "sources": []}

    # Extract final answer
    final_message = result["messages"][-1]
    answer = final_message.content if hasattr(final_message, "content") else str(final_message)

    # Extract sources from semantic_search tool results
    sources = []
    for tr in result.get("tool_results", []):
        if tr["tool"] == "semantic_search":
            try:
                sources.extend(json.loads(tr["result"]))
            except Exception:
                pass

    tool_calls = [
        {"tool": tr["tool"], "args": tr["args"]}
        for tr in result.get("tool_results", [])
    ]

    return {"answer": answer, "tool_calls": tool_calls, "sources": sources[:5]}
