# Quick Start Guide

## 5-Minute Setup

### 1. Start Services

```bash
docker-compose up -d
```

Wait for all containers to start (~30 seconds).

### 2. Pull Models

This will take 5-10 minutes on first run:

```bash
docker exec rag-ollama ollama pull llama3.2
docker exec rag-ollama ollama pull nomic-embed-text
```

### 3. Open Browser

Navigate to: **http://localhost:3000**

### 4. First-Time Configuration

**On first visit:**
- Create admin account
- Set username and password

**Configure Settings:**

1. **Models:**
   - Click Settings (gear icon)
   - Go to Models
   - Set default: `llama3.2:latest`

2. **Web Search:**
   - Settings → Web Search
   - Toggle ON ✅
   - Search Engine: `searxng`
   - SearXNG Query URL: `http://searxng:8080/search?q=<query>`

3. **Code Execution:**
   - Settings → Code Execution
   - Execution Engine: `jupyter`
   - Interpreter Engine: `jupyter`
   - Jupyter Server URL: `http://jupyter:8888`
   - Jupyter Token: `mysecrettoken123`

4. **Documents/RAG:**
   - Settings → Documents
   - Enable RAG ✅
   - Embedding Model: `nomic-embed-text:latest`

### 5. Try It!

**Test Web Search:**
```
Search the web for "what is RLHF" and explain it to me
```

**Test Code Execution:**
```
Write Python code to plot a sine wave
```

**Test RAG (after uploading a PDF):**
```
What does my document say about [topic]?
```

## Done! 🎉

You now have a fully functional local AI research platform.

## Common Commands

**Start everything:**
```bash
docker-compose up -d
```

**Stop everything:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f
```

**Check status:**
```bash
docker-compose ps
```

**Add documents:**
```bash
# Copy PDFs to documents folder, then:
docker exec rag-application python process_pdfs.py
```

## Access Points

- **Main Interface:** http://localhost:3000
- **RAG API:** http://localhost:8000
- **Qdrant Dashboard:** http://localhost:6334/dashboard
- **SearXNG:** http://localhost:8080
- **Jupyter Lab:** http://localhost:8888/lab?token=mysecrettoken123

## Troubleshooting

**Containers not starting?**
```bash
docker-compose logs [service-name]
```

**Out of memory?**
- Increase Docker Desktop memory allocation
- Check `docker stats`

**Models not working?**
```bash
# Verify models are pulled
docker exec rag-ollama ollama list
```

Need help? Check the main [README.md](README.md) for detailed troubleshooting.
