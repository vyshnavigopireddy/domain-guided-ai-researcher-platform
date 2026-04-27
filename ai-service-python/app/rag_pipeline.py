"""
RAG Pipeline: Embeddings → FAISS → LLM
Handles semantic search and context-grounded chat responses.
"""

import os
import json
import pickle
import logging
from typing import List, Tuple, Optional

import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
from openai import OpenAI

logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/faculty_dataset.csv")
INDEX_PATH = os.path.join(os.path.dirname(__file__), "../data/faiss_index.bin")
META_PATH  = os.path.join(os.path.dirname(__file__), "../data/metadata.pkl")

EMBED_MODEL = "all-MiniLM-L6-v2"   # lightweight, fast, high quality
OPENAI_MODEL = "gpt-4o-mini"         # cost-efficient GPT model


class RAGPipeline:
    def __init__(self):
        self.embedder = SentenceTransformer(EMBED_MODEL)
        self.index: Optional[faiss.Index] = None
        self.metadata: List[dict] = []
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        self._load_or_build_index()

    # ─── Index Build / Load ────────────────────────────────────────────────────

    def _load_or_build_index(self):
        if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
            logger.info("Loading existing FAISS index...")
            self.index = faiss.read_index(INDEX_PATH)
            with open(META_PATH, "rb") as f:
                self.metadata = pickle.load(f)
            logger.info(f"Loaded {len(self.metadata)} documents from cache.")
        else:
            logger.info("Building FAISS index from dataset...")
            self._build_index()

    def _build_index(self):
        df = pd.read_csv(DATA_PATH)
        df = df.dropna(subset=["Publication_Title"])
        df = df.drop_duplicates(subset=["Publication_Title"])

        # Build rich text for embedding: title + author + interests
        df["text_for_embedding"] = (
            df["Publication_Title"].fillna("") + " | " +
            df["Name"].fillna("") + " | " +
            df["Interests"].fillna("") + " | " +
            df["Affiliation"].fillna("")
        )

        texts = df["text_for_embedding"].tolist()
        logger.info(f"Encoding {len(texts)} documents...")
        embeddings = self.embedder.encode(texts, show_progress_bar=True, batch_size=64)
        embeddings = np.array(embeddings, dtype="float32")

        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)   # Inner Product ≈ cosine after L2-norm
        self.index.add(embeddings)

        # Build metadata list
        self.metadata = []
        from .clustering import ClusteringEngine
        ce = ClusteringEngine()
        cluster_map = ce.get_researcher_cluster_map()

        for _, row in df.iterrows():
            self.metadata.append({
                "publication_title": str(row.get("Publication_Title", "")),
                "author": str(row.get("Name", "")),
                "affiliation": str(row.get("Affiliation", "")),
                "year": float(row["Year"]) if pd.notna(row.get("Year")) else None,
                "citations": int(row.get("Citations", 0)),
                "interests": str(row.get("Interests", "")),
                "cluster": cluster_map.get(str(row.get("Name", "")), "Uncategorized"),
                "h_index": int(row.get("h_index", 0)),
                "total_citations": int(row.get("Total_Citations", 0)),
            })

        # Persist
        faiss.write_index(self.index, INDEX_PATH)
        with open(META_PATH, "wb") as f:
            pickle.dump(self.metadata, f)
        logger.info("FAISS index built and saved.")

    # ─── Semantic Search ───────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 5,
        cluster_filter: Optional[str] = None,
        min_citations: Optional[int] = None,
    ) -> List[dict]:
        q_emb = self.embedder.encode([query], convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(q_emb)

        # Over-fetch to allow post-filtering
        fetch_k = top_k * 10 if (cluster_filter or min_citations) else top_k
        scores, indices = self.index.search(q_emb, min(fetch_k, len(self.metadata)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            meta = self.metadata[idx]

            # Apply optional filters
            if cluster_filter and meta["cluster"].lower() != cluster_filter.lower():
                continue
            if min_citations and meta["citations"] < min_citations:
                continue

            results.append({**meta, "score": float(score)})
            if len(results) >= top_k:
                break

        return results

    # ─── RAG Chat ─────────────────────────────────────────────────────────────

    def chat(
        self,
        query: str,
        top_k: int = 5,
        chat_history: Optional[List[dict]] = None,
    ) -> Tuple[str, List[dict]]:
        # Step 1: Retrieve relevant documents
        sources = self.search(query, top_k=top_k)

        # Step 2: Build context from retrieved docs
        context_lines = []
        for i, doc in enumerate(sources, 1):
            context_lines.append(
                f"[{i}] Title: {doc['publication_title']}\n"
                f"    Author: {doc['author']} ({doc['affiliation']})\n"
                f"    Year: {doc['year']} | Citations: {doc['citations']}\n"
                f"    Domain: {doc['cluster']}\n"
                f"    Research Interests: {doc['interests']}"
            )
        context = "\n\n".join(context_lines)

        # Step 3: Build prompt
        system_prompt = """You are an expert academic research assistant for the AI Researcher Profiling Platform.
You answer questions about researchers, publications, and academic domains based ONLY on the provided context.
Always cite which documents you are referencing using [1], [2], etc.
If the context does not contain sufficient information, say so clearly.
Be concise, helpful, and specific."""

        messages = [{"role": "system", "content": system_prompt}]

        # Add chat history for multi-turn context
        if chat_history:
            messages.extend(chat_history[-6:])  # last 3 turns

        messages.append({
            "role": "user",
            "content": f"Context from research database:\n\n{context}\n\nQuestion: {query}"
        })

        # Step 4: Call LLM
        if not os.getenv("OPENAI_API_KEY"):
            # Fallback: deterministic answer without LLM
            answer = self._fallback_answer(query, sources)
        else:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=800,
            )
            answer = response.choices[0].message.content

        return answer, sources

    def _fallback_answer(self, query: str, sources: List[dict]) -> str:
        """Rule-based answer when no OpenAI key is provided (demo mode)."""
        if not sources:
            return "No relevant papers found for your query."

        lines = [f"🔍 Based on semantic search for: **{query}**\n"]
        lines.append("Here are the most relevant papers found:\n")
        for i, s in enumerate(sources, 1):
            lines.append(
                f"{i}. **{s['publication_title']}**\n"
                f"   → {s['author']} | {s['affiliation']}\n"
                f"   → Year: {s['year']} | Citations: {s['citations']} | Domain: {s['cluster']}\n"
            )
        lines.append(
            "\n💡 *Note: To enable full AI-powered answers, set the OPENAI_API_KEY environment variable.*"
        )
        return "\n".join(lines)
