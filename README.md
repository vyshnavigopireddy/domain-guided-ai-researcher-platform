# AI Researcher Profiling and Intelligent Query Platform

A production-style full-stack AI-native application demonstrating RAG pipelines, LLM integration, semantic vector search, domain-guided clustering, a LangGraph multi-step agent, and RAGAS-inspired evaluation guardrails — built on real faculty publication data (317 researchers, 52,000+ papers).

---

## System Architecture

```
User (Browser)
     |
     v
+----------------------------------+
|  React Frontend  (port 3000)     |
|  - Semantic Search               |
|  - RAG Chat interface            |
|  - LangGraph AI Agent            |
|  - Domain cluster browser        |
+---------------+------------------+
                | HTTP REST
                v
+----------------------------------+
|  Node.js / Express  (port 3001)  |  <- API Gateway
|  POST /api/search                |
|  POST /api/chat                  |
|  POST /api/agent                 |
|  GET  /api/clusters              |
|  GET  /api/researchers/:name     |
+---------------+------------------+
                | HTTP (axios)
                v
+----------------------------------+
|  FastAPI AI Service  (port 8000) |  <- Python AI Core
|                                  |
|  +---------------------------+   |
|  |  Clustering Engine        |   |
|  |  Interests -> domain      |   |
|  |  10 research clusters     |   |
|  +---------------------------+   |
|                                  |
|  +---------------------------+   |
|  |  RAG Pipeline             |   |
|  |  1. Embed query           |   |
|  |     (SentenceTransformers |   |
|  |      all-MiniLM-L6-v2)   |   |
|  |  2. FAISS similarity      |   |
|  |     search (cosine)       |   |
|  |  3. Build context prompt  |   |
|  |  4. LLM call (GPT-4o-mini)|   |
|  |  5. Return answer+sources |   |
|  +---------------------------+   |
|                                  |
|  +---------------------------+   |
|  |  LangGraph Agent          |   |
|  |  Intent classification    |   |
|  |  Tool routing             |   |
|  |  Answer synthesis         |   |
|  +---------------------------+   |
|                                  |
|  +---------------------------+   |
|  |  Evaluation & Guardrails  |   |
|  |  Faithfulness             |   |
|  |  Answer relevance         |   |
|  |  Context precision        |   |
|  |  Hallucination risk       |   |
|  +---------------------------+   |
+----------------------------------+
```

### Data Flow (step by step)

1. User types a query in the React search bar, chat input, or agent interface
2. React sends a POST request to Node.js (port 3001)
3. Node.js validates input and forwards to FastAPI (port 8000)
4. FastAPI encodes the query into a 384-dimensional embedding (SentenceTransformers)
5. FAISS performs approximate nearest-neighbour search over 52,000+ paper embeddings
6. Top-K results are retrieved with metadata (title, author, citations, cluster)
7. For chat: results are assembled into context and GPT-4o-mini generates a grounded answer
8. For agent: LangGraph classifies intent, routes to tools, and synthesises a final answer with citations
9. RAGAS-inspired metrics are computed on every chat and agent response before it is returned
10. Response flows back: FastAPI -> Node.js -> React -> rendered UI

---

## Project Structure

```
ai-researcher-platform/
|
+-- ai-service-python/              # Python FastAPI AI Core
|   +-- app/
|   |   +-- __init__.py
|   |   +-- main.py                 # FastAPI app, endpoints, startup
|   |   +-- rag_pipeline.py         # Embeddings, FAISS index, LLM integration
|   |   +-- clustering.py           # Domain-guided clustering engine
|   |   +-- agent.py                # LangGraph multi-step agent
|   |   +-- evaluation.py           # RAGAS-inspired evaluation and guardrails
|   +-- tests/
|   |   +-- test_evaluation.py
|   |   +-- eval/
|   |       +-- test_rag_quality.py
|   +-- data/
|   |   +-- faculty_dataset.csv     # Source dataset (317 researchers)
|   |   +-- faiss_index.bin         # Auto-generated on first run
|   |   +-- metadata.pkl            # Auto-generated on first run
|   +-- requirements.txt
|   +-- run.py
|   +-- Dockerfile
|   +-- .env.example
|
+-- backend-node/                   # Node.js Express API Gateway
|   +-- src/
|   |   +-- server.js               # Express app setup
|   |   +-- aiClient.js             # Axios client -> FastAPI
|   |   +-- routes/
|   |       +-- search.js           # POST /api/search
|   |       +-- chat.js             # POST /api/chat
|   |       +-- agent.js            # POST /api/agent
|   |       +-- clusters.js         # GET  /api/clusters
|   |       +-- researchers.js      # GET  /api/researchers/:name
|   +-- package.json
|   +-- Dockerfile
|   +-- .env.example
|
+-- frontend-react/                 # React SPA
|   +-- public/
|   |   +-- index.html
|   +-- src/
|   |   +-- App.jsx                 # Root layout + tab navigation
|   |   +-- App.css                 # Dark-mode design system
|   |   +-- index.js
|   |   +-- api/
|   |   |   +-- client.js           # Centralized fetch client
|   |   +-- components/
|   |       +-- SearchPage.jsx      # Semantic search UI
|   |       +-- ChatPage.jsx        # RAG chat interface
|   |       +-- AgentPage.jsx       # LangGraph agent UI
|   |       +-- ClustersPage.jsx    # Domain cluster explorer
|   |       +-- PaperCard.jsx       # Reusable paper result card
|   |       +-- SearchFilters.jsx   # Filter controls
|   +-- package.json
|   +-- Dockerfile
|   +-- nginx.conf
|
+-- deployment/
|   +-- render/
|   |   +-- render.yaml             # Render.com deployment config
|   +-- terraform/
|       +-- main.tf                 # AWS infrastructure as code
|
+-- .github/
|   +-- workflows/
|       +-- ci-cd.yml               # GitHub Actions CI/CD pipeline
|
+-- docker-compose.yml              # One-command full-stack launch
```

---

## Setup and Running

### Prerequisites

| Tool | Version |
|------|---------|
| Python | >= 3.10 |
| Node.js | >= 18 |
| npm | >= 9 |
| Docker (optional) | >= 24 |

---

### Option A — Run Locally (Recommended for Development)

**Step 1: Extract the project**

```bash
cd ai-researcher-platform
```

**Step 2: Set up the Python AI Service**

```bash
cd ai-service-python

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (optional — system works without it)

# Start the service
python run.py
```

First run: the FAISS index is built from the dataset (approximately 1-2 minutes for 52,000+ papers). Subsequent runs load the index from cache instantly.

Verify: `http://localhost:8000/docs` (Swagger UI)

**Step 3: Set up the Node.js Backend**

```bash
# New terminal
cd backend-node
cp .env.example .env
npm install
npm run dev       # uses nodemon for auto-reload
```

Verify: `http://localhost:3001/health`

**Step 4: Set up the React Frontend**

```bash
# New terminal
cd frontend-react
npm install
npm start
```

App opens at: `http://localhost:3000`

---

### Option B — Docker Compose (One Command)

```bash
# From project root
export OPENAI_API_KEY=sk-...your-key...
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:3001 |
| AI Service | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |

---

## OpenAI API Key

The system is designed to work with or without an OpenAI key:

| Mode | Behavior |
|------|----------|
| With key | Full GPT-4o-mini answers grounded in retrieved context, with agent and evaluation features |
| Without key | Deterministic search results formatted as structured text |

Set the key in `ai-service-python/.env`:

```
OPENAI_API_KEY=sk-...
```

---

## Example Queries to Test

**Semantic Search**

```
cryptographic lattice-based encryption schemes
deep learning for natural language processing
distributed consensus Byzantine fault tolerance
graph algorithms parameterized complexity
quantum error correction codes
privacy-preserving machine learning
protein structure prediction neural networks
```

**Chat / RAG Questions**

```
Who are the top researchers in cryptography?
Suggest papers on deep learning for NLP
Find similar papers to homomorphic encryption
What research is happening in distributed systems?
Which researchers work on quantum computing?
Who are the most cited authors in this database?
Find papers on approximation algorithms published after 2015
What is the h-index of researchers in machine learning?
```

**AI Agent Queries**

```
Compare the top researchers in machine learning and cryptography
Who has the highest h-index in distributed systems?
Recommend papers related to attention mechanisms in NLP
Give me a full profile of researchers working on lattice-based cryptography
```

**Cluster-Aware Search (with domain filter)**

- Select "Machine Learning and AI" and search "attention mechanisms"
- Select "Cryptography and Security" and search "post-quantum schemes"
- Set min_citations = 500 to retrieve only highly cited papers

---

## How RAG, the Agent, and Clustering Are Integrated

### 1. Domain-Guided Clustering (offline, pre-computed)

```
faculty_dataset.csv
     |
     v
ClusteringEngine.classify_domain(interests)
     |  <- keyword matching against 10 domain taxonomies
     v
researcher -> cluster label
  e.g. "Shweta Agrawal" -> "Cryptography & Security"
       "John Doe"        -> "Machine Learning & AI"
```

Each paper in the FAISS index carries its author's cluster label, enabling cluster-aware filtering during retrieval.

### 2. RAG Pipeline (online, per-query)

```
User Query: "who works on lattice cryptography?"
     |
     v  SentenceTransformer.encode()
Query Embedding (384-dim float32 vector)
     |
     v  faiss.IndexFlatIP.search(query_emb, top_k=5)
Retrieved Papers (ranked by cosine similarity)
  [1] "Efficient lattice IBE" — Shweta Agrawal — 1347 citations
  [2] "Lattice basis delegation" — Shweta Agrawal — 559 citations
  ...
     |
     v  Build context string
"[1] Title: Efficient lattice IBE
     Author: Shweta Agrawal (IIT Madras)
     Citations: 1347 | Domain: Cryptography & Security ..."
     |
     v  GPT-4o-mini chat completion
     System: "Answer ONLY from provided context, cite [1],[2]..."
     User:   context + question
     |
     v
AI Answer with citations and RAGAS-style evaluation metrics
```

### 3. LangGraph Agent (multi-step, tool-using)

The agent follows a ReAct-style graph:

```
START -> classify_intent -> [tool_node] -> synthesise -> END
```

Available tools:

- `semantic_search` — FAISS nearest-neighbour search over 52,000+ papers
- `researcher_profile` — full profile for a named researcher
- `cluster_overview` — summary of a domain cluster

The agent classifies the user's intent (search, compare, profile, or recommend), routes to the appropriate tool or tools, and synthesises a grounded final answer with citations.

### 4. Evaluation and Guardrails

Every chat and agent response is evaluated before being returned. Metrics computed include faithfulness (how grounded the answer is in retrieved context), answer relevance (how well the answer addresses the question), context precision (whether retrieved documents are relevant to the query), and hallucination risk (a heuristic score based on unverifiable claims).

Input guardrails block harmful or off-topic queries before they reach the pipeline. Output guardrails suppress answers that fall below faithfulness thresholds.

### 5. Cluster-Aware Retrieval

```python
# Filter FAISS results to a specific domain
results = rag_pipeline.search(
    query="attention mechanisms",
    cluster_filter="Machine Learning & AI",   # cluster integration
    min_citations=100                          # citation ranking
)
```

This combines domain clustering with semantic vector search — papers must be both semantically relevant and belong to the target domain cluster.

---

## API Reference

### FastAPI Endpoints (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| POST | `/search` | Semantic search over publications |
| POST | `/chat` | RAG-based Q&A with LLM and evaluation |
| POST | `/agent` | LangGraph multi-step agentic query |
| GET | `/evaluate/retrieval` | Retrieval-only evaluation (CI quality gate) |
| GET | `/clusters` | All domain clusters with stats |
| GET | `/clusters/{name}/researchers` | Researchers in a cluster |
| GET | `/researchers/{name}` | Full researcher profile |

**POST /search body:**

```json
{
  "query": "lattice cryptography",
  "top_k": 5,
  "cluster_filter": "Cryptography & Security",
  "min_citations": 100
}
```

**POST /chat body:**

```json
{
  "query": "Who are key researchers in NLP?",
  "top_k": 5,
  "chat_history": [
    {"role": "user", "content": "previous question"},
    {"role": "assistant", "content": "previous answer"}
  ]
}
```

**POST /agent body:**

```json
{
  "query": "Compare the top researchers in cryptography and machine learning",
  "chat_history": []
}
```

**POST /agent response includes:**

```json
{
  "answer": "...",
  "tool_calls": [...],
  "sources": [...],
  "query": "...",
  "evaluation": {
    "faithfulness": 0.91,
    "answer_relevance": 0.87,
    "context_precision": 0.83,
    "hallucination_risk": 0.05
  }
}
```

### Node.js Endpoints (port 3001)

| Method | Path | Proxies To |
|--------|------|------------|
| POST | `/api/search` | `/search` |
| POST | `/api/chat` | `/chat` |
| POST | `/api/agent` | `/agent` |
| GET | `/api/clusters` | `/clusters` |
| GET | `/api/clusters/:name/researchers` | `/clusters/{name}/researchers` |
| GET | `/api/researchers/:name` | `/researchers/{name}` |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 18 | SPA with search, chat, agent, and cluster UI |
| API Gateway | Node.js + Express | Routing, validation, CORS |
| AI Service | Python + FastAPI | Embeddings, FAISS, LLM, agent, evaluation |
| Embeddings | SentenceTransformers (all-MiniLM-L6-v2) | Text to 384-dimensional vectors |
| Vector DB | FAISS (IndexFlatIP) | Cosine similarity search |
| LLM | OpenAI GPT-4o-mini | Context-grounded answers |
| Agent | LangGraph + LangChain | Multi-step tool-using agent |
| Evaluation | Custom RAGAS-inspired metrics | Faithfulness, relevance, precision, hallucination risk |
| Clustering | Custom keyword taxonomy | Domain classification |
| Dataset | Faculty CSV | 317 researchers, 52,000+ papers |
| CI/CD | GitHub Actions | Lint, test, RAG quality gate, Docker build, AWS ECS deploy |
| Infrastructure | Terraform + AWS ECS / ECR | Container orchestration and registry |

---

## CI/CD Pipeline

The GitHub Actions workflow runs five stages on every push and pull request:

1. **Lint** — Python (ruff) and Node.js (eslint)
2. **Test** — Python unit tests and Node.js Jest tests
3. **AI Eval** — RAG quality gate; context precision must be >= 0.5
4. **Build and Push** — Docker images pushed to AWS ECR (main branch only)
5. **Deploy** — ECS services updated with the new images (main branch only)

Required GitHub Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_ACCOUNT_ID`, `OPENAI_API_KEY`

---

## Deployment

### Render (render.yaml)

A `render.yaml` is provided under `deployment/render/` for one-click deployment to Render.com.

### AWS (Terraform)

A full Terraform configuration is provided under `deployment/terraform/` for provisioning the required AWS infrastructure (ECS, ECR, VPC, load balancer).

---

## Python Dependencies

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
pydantic==2.7.1
sentence-transformers==3.0.1
faiss-cpu==1.8.0
numpy==1.26.4
pandas==2.2.2
openai==1.35.3
langchain==0.2.6
langchain-core==0.2.22
langchain-openai==0.1.14
langgraph==0.1.14
python-dotenv==1.0.1
httpx==0.27.0
```
