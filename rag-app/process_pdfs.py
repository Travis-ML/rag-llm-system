import os
import glob
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://rag-ollama:11434")
QDRANT_HOST = os.getenv("QDRANT_HOST", "rag-qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "documents"

print("Initializing...")
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url=OLLAMA_HOST
)

qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Create collection if it doesn't exist
print(f"Checking for collection: {COLLECTION_NAME}")
collections = qdrant_client.get_collections().collections
if not any(c.name == COLLECTION_NAME for c in collections):
    print(f"Creating collection: {COLLECTION_NAME}")
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE)
    )
    print("Collection created successfully!")
else:
    print("Collection already exists")

vectorstore = QdrantVectorStore(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
    embedding=embeddings
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

# Process all PDFs
pdf_files = glob.glob("/documents/*.pdf")
print(f"Found {len(pdf_files)} PDF files")

for pdf_path in pdf_files:
    print(f"\nProcessing: {os.path.basename(pdf_path)}")
    try:
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        print(f"  - Loaded {len(documents)} pages")
        
        splits = text_splitter.split_documents(documents)
        print(f"  - Created {len(splits)} chunks")
        
        vectorstore.add_documents(splits)
        print(f"  ✓ Indexed successfully")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n✓ Processing complete!")

try:
    collection_info = qdrant_client.get_collection(COLLECTION_NAME)
    print(f"\nTotal points in database: {collection_info.points_count}")
except Exception as e:
    print(f"\nCould not retrieve stats: {e}")