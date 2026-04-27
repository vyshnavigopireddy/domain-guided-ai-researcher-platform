/**
 * Centralized API client for the React frontend.
 * - In Docker: REACT_APP_API_URL is empty → uses relative /api/... paths (nginx proxies to backend)
 * - In local dev: REACT_APP_API_URL=http://localhost:3001 → direct backend calls
 */

const BASE_URL = process.env.REACT_APP_API_URL || '';

async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

export const api = {
  /** Semantic search over publications */
  search: (query, topK = 5, clusterFilter = null, minCitations = null) =>
    apiFetch('/api/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        top_k: topK,
        ...(clusterFilter && { cluster_filter: clusterFilter }),
        ...(minCitations && { min_citations: minCitations }),
      }),
    }),

  /** RAG-based conversational Q&A */
  chat: (query, chatHistory = [], topK = 5) =>
    apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ query, chat_history: chatHistory, top_k: topK }),
    }),

  /** LangGraph agentic Q&A with tool call trace + eval metrics */
  agent: (query, chatHistory = []) =>
    apiFetch('/api/agent', {
      method: 'POST',
      body: JSON.stringify({ query, chat_history: chatHistory }),
    }),

  /** All domain clusters */
  getClusters: () => apiFetch('/api/clusters'),

  /** Researchers in a specific cluster */
  getClusterResearchers: (clusterName) =>
    apiFetch(`/api/clusters/${encodeURIComponent(clusterName)}/researchers`),

  /** Single researcher profile */
  getResearcher: (name) =>
    apiFetch(`/api/researchers/${encodeURIComponent(name)}`),
};
