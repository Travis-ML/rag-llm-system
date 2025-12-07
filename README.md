# Local RAG System with AI Agents

A complete self-hosted AI research platform running on Docker with GPU acceleration. Combines LLM inference, vector search, web search, and code execution - all running locally.

## 🎯 What This Does

- **RAG (Retrieval-Augmented Generation)**: Query your PDF documents with AI
- **Web Search**: AI-powered web search with real-time results
- **Code Execution**: Run Python code through Jupyter integration
- **Multi-Modal Chat**: Single interface for all capabilities
- **100% Local**: Runs on your hardware with GPU acceleration

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Open WebUI                          │
│              (Single Interface for Everything)          │
└──────────────┬──────────────────┬────────────────┬──────┘
               │                  │                │
        ┌──────▼──────┐    ┌──────▼──────┐   ┌─────▼─────┐
        │   Ollama    │    │   SearXNG   │   │  Jupyter  │
        │ (LLM + GPU) │    │ (Web Search)│   │(Code Exec)│
        └──────┬──────┘    └─────────────┘   └───────────┘
               │
        ┌──────▼──────┐   ┌─────────────┐
        │   Qdrant    │   │  RAG API    │
        │ (Vector DB) │───│  (Custom)   │
        └─────────────┘   └─────────────┘
```

## 📦 Components

| Service | Purpose | Port | GPU |
|---------|---------|------|-----|
| **Ollama** | LLM inference (llama3.2, nomic-embed-text) | 11434 | ✅ RTX 4070 |
| **Qdrant** | Vector database for embeddings | 6333/6334 | ❌ |
| **RAG API** | Custom RAG implementation (FastAPI) | 8000 | ❌ |
| **SearXNG** | Meta-search engine (privacy-focused) | 8080 | ❌ |
| **Open WebUI** | ChatGPT-like interface | 3000 | ❌ |
| **Jupyter** | Code execution environment | 8888 | ❌ |

## 🚀 Quick Start

### Prerequisites

- Docker Desktop with WSL2
- NVIDIA GPU with drivers installed
- NVIDIA Container Toolkit
- 16GB+ RAM recommended
- 20GB+ disk space

### Installation

1. **Clone this repository:**
```bash
git clone https://github.com/Travis-ML/rag-llm-system.git
cd rag-llm-system/rag-system
```

2. **Start all services:**
```bash
docker-compose up -d
```

3. **Pull required models:**
```bash
docker exec rag-ollama ollama pull llama3.2
docker exec rag-ollama ollama pull nomic-embed-text
```

4. **Access interfaces:**
- Open WebUI: http://localhost:3000
- Qdrant Dashboard: http://localhost:6334/dashboard
- SearXNG: http://localhost:8080
- Jupyter Lab: http://localhost:8888/lab?token=mysecrettoken123
- RAG API: http://localhost:8000

### First-Time Setup

**Configure Open WebUI:**

1. Create admin account on first visit
2. Go to Settings → Models → Set default to `llama3.2:latest`
3. Settings → Web Search:
   - Enable Web Search ✅
   - Search Engine: `searxng`
   - SearXNG URL: `http://searxng:8080/search?q=<query>`
4. Settings → Code Execution:
   - Execution Engine: `jupyter`
   - Jupyter URL: `http://jupyter:8888`
   - Token: `mysecrettoken123`
5. Settings → Documents:
   - Enable RAG ✅
   - Embedding Model: `nomic-embed-text:latest`

## 📚 Adding Documents

### Method 1: Upload via Open WebUI
1. Click the `+` icon
2. Upload PDFs directly
3. They auto-index to Qdrant

### Method 2: Bulk Processing
1. Copy PDFs to `./documents/` folder
2. Process them:
```bash
docker exec rag-application python process_pdfs.py
```

### Method 3: Via API
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@/path/to/document.pdf"
```

## 💬 Usage Examples

### Document Q&A
```
What does my RLHF paper say about reward models?
```

### Web Search + RAG
```
Compare recent developments in RLHF with what's in my documents
```

### Code Execution
```
Write Python code to analyze the first 100 Fibonacci numbers and plot them
```

### Multi-Step Research
```
1. Search the web for latest adversarial AI attacks
2. Check if my papers mention any of these attacks
3. Write code to simulate a simple prompt injection attack
```

## 🛠️ Development

### Project Structure
```
rag-system/
├── docker-compose.yml       # Main orchestration
├── rag-app/                # Custom RAG API
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── rag_server.py       # FastAPI server
│   └── process_pdfs.py     # PDF indexing script
├── documents/              # PDF storage
└── README.md
```

### Updating Components

**Rebuild RAG API:**
```bash
docker-compose down rag-app
docker-compose build rag-app
docker-compose up -d rag-app
```

**Update models:**
```bash
docker exec rag-ollama ollama pull llama3.2:latest
```

**Reset vector database:**
```bash
docker-compose down -v qdrant
docker-compose up -d qdrant
```

## 🔧 Troubleshooting

### Out of Memory
- Increase Docker Desktop memory: Settings → Resources → 16GB+
- Configure WSL2 memory in `~/.wslconfig`:
```ini
[wsl2]
memory=16GB
processors=8
```

### Container Exits with Code 137
- OOM killed - increase memory allocation
- Check: `docker stats`

### Can't Connect to Ollama
```bash
# Check if running
docker-compose ps

# Test connection
curl http://localhost:11434/api/tags
```

### Web Search Not Working
- Verify SearXNG URL in Open WebUI settings
- Test SearXNG directly: http://localhost:8080

### Code Execution Fails
- Check Jupyter token matches in settings
- Verify connection: http://localhost:8888

## 📊 Performance

**On RTX 4070 (12GB VRAM):**
- LLM Response Time: 2-5 seconds
- Vector Search: <100ms
- Document Indexing: ~30 chunks/second
- Code Execution: Near-instant

**Resource Usage:**
- Ollama: ~4GB VRAM (llama3.2)
- Qdrant: ~150MB RAM
- Open WebUI: ~300MB RAM
- Total: ~6GB RAM, 4GB VRAM

## 🔒 Security Notes

- All services run locally - no data leaves your machine
- Change default tokens in production
- SearXNG provides privacy-focused web search
- Jupyter token should be changed in `docker-compose.yml`

## 🎓 Use Cases

- **AI Security Research**: Test adversarial attacks safely
- **Document Analysis**: Query research papers, reports, manuals
- **Research Assistant**: Web search + knowledge base + code execution
- **Learning**: Experiment with LLMs, RAG, vector databases
- **Privacy**: Keep all AI interactions local

## 📝 Configuration

### Environment Variables

**Ollama:**
- `OLLAMA_HOST`: Default `http://rag-ollama:11434`

**RAG API:**
- `QDRANT_HOST`: Vector database host
- `QDRANT_PORT`: Default `6333`
- `OLLAMA_HOST`: LLM endpoint

**Jupyter:**
- `JUPYTER_TOKEN`: Authentication token
- `JUPYTER_ENABLE_LAB`: Enable JupyterLab interface

## 🤝 Contributing

This is a personal research setup. Fork and modify as needed!

## 📄 License

MIT License - Use freely for research and learning

## 🙏 Acknowledgments

Built with:
- [Ollama](https://ollama.ai/) - Local LLM inference
- [Qdrant](https://qdrant.tech/) - Vector database
- [Open WebUI](https://github.com/open-webui/open-webui) - Chat interface
- [SearXNG](https://github.com/searxng/searxng) - Meta-search
- [LangChain](https://github.com/langchain-ai/langchain) - RAG framework
- [FastAPI](https://fastapi.tiangolo.com/) - API framework

## 🔗 Resources

- [Documentation](docs/) - Detailed guides (coming soon)
- [Examples](examples/) - Usage examples (coming soon)
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues (coming soon)

---

**Built for AI Security Research** | **100% Local & Private** | **GPU Accelerated**
