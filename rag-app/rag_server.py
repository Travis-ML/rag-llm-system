from fastapi import FastAPI, UploadFile, File
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from qdrant_client import QdrantClient
import os
import uvicorn

app = FastAPI(title="RAG System API")

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://rag-ollama:11434")
QDRANT_HOST = os.getenv("QDRANT_HOST", "rag-qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "documents"

# Initialize components
print("Initializing LLM...")
llm = OllamaLLM(
    model="llama3.2",
    base_url=OLLAMA_HOST
)

print("Initializing embeddings...")
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url=OLLAMA_HOST
)

print("Connecting to Qdrant...")
qdrant_client = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT
)

vectorstore = QdrantVectorStore(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
    embedding=embeddings
)

# Create text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

# RAG prompt template
RAG_TEMPLATE = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Context:
{context}

Question: {question}

Answer:"""

@app.get("/")
async def root():
    return {
        "status": "running",
        "message": "RAG System API",
        "endpoints": {
            "upload": "/upload",
            "query": "/query?q=your_question",
            "stats": "/stats"
        }
    }

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a document (PDF or TXT)"""
    try:
        # Save uploaded file
        file_path = f"/documents/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Load document
        if file.filename.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file.filename.endswith('.txt'):
            loader = TextLoader(file_path)
        else:
            return {"error": "Unsupported file type. Use PDF or TXT"}
        
        documents = loader.load()
        
        # Split documents
        splits = text_splitter.split_documents(documents)
        
        # Add to vector store
        vectorstore.add_documents(splits)
        
        return {
            "status": "success",
            "filename": file.filename,
            "chunks_created": len(splits)
        }
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/query")
async def query_documents(q: str, k: int = 4):
    """Query the RAG system"""
    try:
        # Use similarity_search from QdrantVectorStore
        relevant_docs = vectorstore.similarity_search(q, k=k)
        
        # Build context from retrieved docs
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # Create prompt
        prompt = RAG_TEMPLATE.format(context=context, question=q)
        
        # Get answer from LLM
        answer = llm.invoke(prompt)
        
        return {
            "question": q,
            "answer": answer,
            "source_documents": [
                {
                    "content": doc.page_content[:200] + "...",
                    "metadata": doc.metadata
                }
                for doc in relevant_docs
            ]
        }
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/stats")
async def get_stats():
    """Get vector store statistics"""
    try:
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        return {
            "collection": COLLECTION_NAME,
            "points_count": collection_info.points_count,
            "status": collection_info.status
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("Starting RAG server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)