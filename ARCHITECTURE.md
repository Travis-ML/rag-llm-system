# Architecture Documentation

Detailed technical architecture of the Local RAG System.

## System Overview

This is a microservices-based AI research platform where each component runs in its own Docker container, communicating over a shared network.

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         User                                  │
│                      (Web Browser)                            │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ HTTP (Port 3000)
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                      Open WebUI                               │
│              (Chat Interface & Orchestrator)                  │
│                                                               │
│  Features:                                                    │
│  • Chat UI (ChatGPT-like)                                    │
│  • Tool orchestration                                        │
│  • Session management                                        │
│  • File uploads                                              │
└──────────┬────────────┬───────────┬──────────────────────────┘
           │            │           │
           │            │           │
           ▼            ▼           ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │  Ollama  │  │ SearXNG  │  │ Jupyter  │
   │   LLM    │  │   Web    │  │   Code   │
   │          │  │  Search  │  │   Exec   │
   └────┬─────┘  └──────────┘  └──────────┘
        │
        │ Embeddings & Generation
        │
   ┌────▼─────┐       ┌──────────┐
   │ Qdrant   │◄──────│ RAG API  │
   │ Vector   │       │ Custom   │
   │    DB    │       │ FastAPI  │
   └──────────┘       └──────────┘
```

## Component Details

### 1. Open WebUI (Port 3000)

**Role:** Main user interface and orchestration layer

**Responsibilities:**
- Present chat interface to user
- Detect when tools are needed (web search, code execution, RAG)
- Route requests to appropriate services
- Aggregate responses from multiple sources
- Manage user sessions and chat history

**Technology:**
- Framework: SvelteKit (frontend) + Python FastAPI (backend)
- Database: SQLite (user data, chat history)
- Authentication: Built-in user management

**Communication:**
- → Ollama: HTTP REST API (LLM inference, embeddings)
- → SearXNG: HTTP REST API (web search)
- → Jupyter: Jupyter Kernel Gateway protocol (code execution)
- → Qdrant: HTTP REST API (vector search)

### 2. Ollama (Port 11434)

**Role:** Local LLM inference engine with GPU acceleration

**Models Hosted:**
- `llama3.2:latest` (8B parameters) - Chat/generation
- `nomic-embed-text:latest` (137M parameters) - Text embeddings

**Responsibilities:**
- Generate chat responses
- Create text embeddings for RAG
- Process prompts with context from other tools

**Technology:**
- Built on: llama.cpp
- Acceleration: CUDA (NVIDIA GPU)
- API: OpenAI-compatible REST API

**Resource Usage:**
- VRAM: ~4GB (llama3.2 loaded)
- Response time: 2-5 seconds (depending on prompt length)

**GPU Optimization:**
- Full model loaded into VRAM
- Concurrent requests queued
- KV-cache for faster repeated queries

### 3. Qdrant (Ports 6333, 6334)

**Role:** Vector database for semantic search

**Responsibilities:**
- Store document embeddings (768-dimensional vectors)
- Perform similarity search (cosine distance)
- Return relevant chunks for RAG queries

**Technology:**
- Language: Rust
- Storage: HNSW index (Hierarchical Navigable Small World)
- API: REST (6333) and gRPC (6334)

**Collections:**
- `documents` - Main collection for PDFs
  - Vector size: 768 (nomic-embed-text dimensions)
  - Distance metric: Cosine similarity
  - Indexed: ~6,000 chunks (from 4 PDFs in example)

**Performance:**
- Query time: <100ms for k=4 similarity search
- Indexing: ~30 chunks/second

### 4. RAG API (Port 8000)

**Role:** Custom RAG implementation with FastAPI

**Endpoints:**

```python
GET  /              # Health check
POST /upload        # Upload and index documents
GET  /query?q=...   # Query with RAG
GET  /stats         # Database statistics
```

**Workflow:**

**Document Upload:**
1. Receive PDF via POST
2. Extract text with PyPDF
3. Split into chunks (1000 chars, 200 overlap)
4. Generate embeddings via Ollama
5. Store in Qdrant

**Query:**
1. Receive question
2. Generate query embedding
3. Search Qdrant for k=4 similar chunks
4. Build prompt with context
5. Send to Ollama for generation
6. Return answer + sources

**Technology:**
- Framework: FastAPI
- PDF Processing: PyPDF
- Text Splitting: RecursiveCharacterTextSplitter
- Embeddings: langchain-ollama
- Vector Store: langchain-qdrant

### 5. SearXNG (Port 8080)

**Role:** Meta-search engine for web queries

**Features:**
- Aggregates results from multiple engines
- Privacy-focused (no tracking)
- Customizable search engines

**Configured Engines:**
- Google
- DuckDuckGo
- Bing
- arXiv (academic papers)
- GitHub (code search)

**Usage:**
```
http://searxng:8080/search?q=<query>
```

Returns HTML with search results that Open WebUI parses.

### 6. Jupyter (Port 8888)

**Role:** Python code execution environment

**Capabilities:**
- Execute arbitrary Python code
- Access to scientific libraries (numpy, pandas, matplotlib)
- Generate plots/visualizations
- File I/O operations

**Security:**
- Runs in isolated container
- Token-based authentication
- No network access to host (only Docker network)

**Integration:**
- Open WebUI connects via Jupyter Gateway Protocol
- Code sent → Executed → Results returned
- Supports text output, images (base64), errors

## Data Flow Examples

### Example 1: Simple Chat

```
User: "What is RLHF?"
  ↓
Open WebUI
  ↓ (HTTP POST with prompt)
Ollama (llama3.2)
  ↓ (Generated response)
Open WebUI
  ↓
User sees answer
```

### Example 2: Web Search Query

```
User: "Search for latest RLHF developments"
  ↓
Open WebUI (detects search intent)
  ├─► SearXNG
  │     ↓ (search results HTML)
  │   Open WebUI (parses results)
  └─► Formats context with search results
  ↓
Ollama (llama3.2 with search context)
  ↓ (synthesized answer)
Open WebUI
  ↓
User sees answer with sources
```

### Example 3: RAG Query

```
User: "What does my RLHF paper say about reward models?"
  ↓
Open WebUI (detects document query)
  ↓ (embedding request)
Ollama (nomic-embed-text)
  ↓ (query vector)
Qdrant (similarity search)
  ↓ (relevant chunks)
Open WebUI (builds context)
  ↓ (prompt + chunks)
Ollama (llama3.2)
  ↓ (answer based on docs)
Open WebUI
  ↓
User sees answer with document sources
```

### Example 4: Code Execution

```
User: "Plot a sine wave"
  ↓
Open WebUI (detects code request)
  ↓ (prompt)
Ollama (llama3.2 generates code)
  ↓ (Python code)
Open WebUI
  ↓ (execute request)
Jupyter
  ↓ (execution + plot)
Open WebUI (renders results)
  ↓
User sees code + plot
```

### Example 5: Multi-Tool Query

```
User: "Search the web for RLHF, compare with my docs, 
       then write code to analyze sentiment"
  ↓
Open WebUI (orchestrates multiple tools)
  ├─► SearXNG (web results)
  ├─► Qdrant (document chunks)
  └─► Combines contexts
  ↓
Ollama (synthesizes + generates code)
  ↓
Open WebUI
  ↓ (execute code)
Jupyter
  ↓ (results)
Open WebUI (final response)
  ↓
User sees: web summary + doc comparison + analysis code + results
```

## Network Architecture

All containers communicate via Docker network: `rag-network`

```
┌─────────────────────────────────────────────────────┐
│              Docker Network: rag-network            │
│                    (Bridge Mode)                    │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │  open-webui  │  │  rag-ollama  │                 │
│  │ :3000→:8080  │  │ :11434       │                 │
│  └──────────────┘  └──────────────┘                 │
│                                                     │
│    ┌──────────────┐  ┌──────────────┐               │
│    │  searxng     │  │   jupyter    │               │
│    │ :8080        │  │ :8888        │               │
│    └──────────────┘  └──────────────┘               │
│                                                     │
│    ┌──────────────┐  ┌──────────────┐               │
│    │  rag-qdrant  │  │ rag-app      │               │
│    │ :6333, :6334 │  │ :8000        │               │
│    └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────┘
         │
         │ Port Forwarding to Host
         ↓
    Windows Host (localhost)
```

**Container DNS:**
- Containers reference each other by service name
- Example: `http://rag-ollama:11434` (not localhost)

## Storage Architecture

### Docker Volumes (Persistent)

```
ollama-data:        /root/.ollama           # Model files (~5GB)
qdrant-data:        /qdrant/storage         # Vector database
open-webui-data:    /app/backend/data       # User data, chats
searxng-data:       /etc/searxng            # Search config
jupyter-data:       /home/jovyan/work       # Notebooks, outputs
```

### Bind Mounts (Host Filesystem)

```
./documents  →  /documents  # PDFs shared with containers
```

## Security Model

### Container Isolation
- Each service runs in isolated container
- No direct host access (except bind mounts)
- Services only communicate via Docker network

### Authentication
- **Open WebUI:** Username/password (first user = admin)
- **Jupyter:** Token-based (`mysecrettoken123`)
- **Qdrant:** No auth (only accessible via Docker network)
- **Ollama:** No auth (local only)

### Data Privacy
- **All processing is local** - no data leaves your machine
- No telemetry or external API calls
- Web searches go through SearXNG (privacy-focused)

### GPU Access
- Only Ollama container has GPU access
- Jupyter can be configured for GPU if needed
- Uses NVIDIA Container Toolkit

## Scalability Considerations

### Current Limitations
- Single GPU (RTX 4070 - 12GB VRAM)
- Single model loaded at a time in Ollama
- Qdrant runs single-node (no clustering)
- Jupyter single-kernel execution

### Potential Optimizations
- **Multiple Models:** Run multiple Ollama instances
- **GPU Sharing:** Allocate VRAM splits for concurrent models
- **Qdrant Clustering:** Distribute vector storage
- **Load Balancing:** Add nginx for multiple Open WebUI instances

## Monitoring & Observability

### Resource Monitoring
```bash
docker stats  # Real-time container resource usage
```

### Logs
```bash
docker-compose logs -f [service]  # View service logs
```

### Health Checks
- Open WebUI: http://localhost:3000
- Ollama: http://localhost:11434/api/tags
- Qdrant: http://localhost:6334/dashboard
- RAG API: http://localhost:8000
- SearXNG: http://localhost:8080

## Technology Stack Summary

| Layer | Technology |
|-------|-----------|
| **Frontend** | SvelteKit (Open WebUI) |
| **Backend** | Python FastAPI |
| **LLM Runtime** | Ollama (llama.cpp) |
| **Vector DB** | Qdrant (Rust) |
| **Search** | SearXNG (Python) |
| **Code Exec** | Jupyter (IPython) |
| **Orchestration** | Docker Compose |
| **GPU** | CUDA 12.1, NVIDIA Container Toolkit |
| **Network** | Docker Bridge Network |
| **Storage** | Docker Volumes + Bind Mounts |

## Future Enhancements

Potential additions to the architecture:

1. **LangFlow Integration** - Visual agent builder
2. **n8n Workflows** - Automated research pipelines
3. **Redis Cache** - Speed up repeated queries
4. **PostgreSQL** - Replace SQLite for multi-user scenarios
5. **Nginx Reverse Proxy** - Single entry point, SSL termination
6. **Prometheus + Grafana** - Advanced monitoring
7. **MinIO** - S3-compatible object storage for large files

---

This architecture provides a solid foundation for AI research while maintaining privacy, performance, and flexibility.
