"""
AI Researcher Profiling & Intelligent Query Platform
FastAPI AI Service - Main Application
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Optional, List, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .rag_pipeline import RAGPipeline
from .clustering import ClusteringEngine
from .evaluation import evaluator, check_query_safety, check_answer_safety
from .agent import init_agent_dependencies, run_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

rag_pipeline: Optional[RAGPipeline] = None
clustering_engine: Optional[ClusteringEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_pipeline, clustering_engine
    logger.info("Initializing RAG pipeline and clustering engine...")
    rag_pipeline = RAGPipeline()
    clustering_engine = ClusteringEngine()
    init_agent_dependencies(rag_pipeline, clustering_engine)
    logger.info("✅ AI service ready.")
    yield
    logger.info("Shutting down AI service.")


app = FastAPI(
    title="AI Researcher Profiling - AI Service",
    description="RAG pipeline + LangGraph agent + evaluation guardrails",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    cluster_filter: Optional[str] = None
    min_citations: Optional[int] = None

class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    chat_history: Optional[List[dict]] = []

class AgentRequest(BaseModel):
    query: str
    chat_history: Optional[List[dict]] = []

class SearchResult(BaseModel):
    publication_title: str
    author: str
    affiliation: str
    year: Optional[float]
    citations: int
    interests: str
    cluster: str
    score: float

class ChatResponse(BaseModel):
    answer: str
    sources: List[SearchResult]
    query: str
    evaluation: Optional[dict] = None

class AgentResponse(BaseModel):
    answer: str
    tool_calls: List[dict]
    sources: List[Any]
    query: str
    evaluation: Optional[dict] = None


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "rag_ready": rag_pipeline is not None,
        "agent_ready": True,
        "version": "2.0.0",
    }


@app.post("/search", response_model=List[SearchResult])
async def semantic_search(request: SearchRequest):
    """Semantic search with input guardrail."""
    safety = check_query_safety(request.query)
    if not safety.allowed:
        raise HTTPException(status_code=400, detail=f"Query blocked: {safety.reason}")
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    try:
        results = rag_pipeline.search(
            query=request.query,
            top_k=request.top_k,
            cluster_filter=request.cluster_filter,
            min_citations=request.min_citations,
        )
        return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def rag_chat(request: ChatRequest):
    """RAG-based Q&A with RAGAS-style evaluation on every response."""
    safety = check_query_safety(request.query)
    if not safety.allowed:
        raise HTTPException(status_code=400, detail=f"Query blocked: {safety.reason}")
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    try:
        t0 = time.time()
        answer, sources = rag_pipeline.chat(
            query=request.query,
            top_k=request.top_k,
            chat_history=request.chat_history,
        )
        latency_ms = (time.time() - t0) * 1000
        eval_result = evaluator.evaluate(request.query, answer, sources, latency_ms)
        answer_guard = check_answer_safety(answer, eval_result)
        if not answer_guard.allowed:
            logger.warning(f"Answer blocked: {answer_guard.reason}")
            answer = (
                "⚠️ The generated answer did not meet quality thresholds. "
                "Please rephrase your question or try a more specific query."
            )
        return ChatResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            evaluation=eval_result.to_dict(),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent", response_model=AgentResponse)
async def agent_query(request: AgentRequest):
    """
    LangGraph multi-step agentic endpoint.
    Autonomously selects tools and synthesises a grounded answer.
    """
    safety = check_query_safety(request.query)
    if not safety.allowed:
        raise HTTPException(status_code=400, detail=f"Query blocked: {safety.reason}")
    try:
        t0 = time.time()
        result = run_agent(request.query, request.chat_history)
        latency_ms = (time.time() - t0) * 1000
        eval_result = evaluator.evaluate(
            request.query, result["answer"], result.get("sources", []), latency_ms
        )
        return AgentResponse(
            answer=result["answer"],
            tool_calls=result["tool_calls"],
            sources=result["sources"],
            query=request.query,
            evaluation=eval_result.to_dict(),
        )
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evaluate/retrieval")
async def evaluate_retrieval(query: str, top_k: int = 5):
    """Retrieval-only evaluation — useful in CI quality gates."""
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    docs = rag_pipeline.search(query, top_k=top_k)
    return evaluator.evaluate_retrieval_only(query, docs)


@app.get("/clusters")
async def get_clusters():
    if not clustering_engine:
        raise HTTPException(status_code=503, detail="Clustering engine not initialized")
    try:
        return clustering_engine.get_clusters()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/clusters/{cluster_name}/researchers")
async def get_cluster_researchers(cluster_name: str):
    if not clustering_engine:
        raise HTTPException(status_code=503, detail="Clustering engine not initialized")
    try:
        return clustering_engine.get_cluster_researchers(cluster_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/researchers/{name}")
async def get_researcher_profile(name: str):
    if not clustering_engine:
        raise HTTPException(status_code=503, detail="Clustering engine not initialized")
    try:
        profile = clustering_engine.get_researcher_profile(name)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Researcher '{name}' not found")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
