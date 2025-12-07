import os
import subprocess

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://rag-ollama:11434")

print("Pulling required models...")
print("This may take a while on first run...")

# Pull LLM
subprocess.run(["ollama", "pull", "llama3.2"])

# Pull embedding model
subprocess.run(["ollama", "pull", "nomic-embed-text"])

print("Models ready!")