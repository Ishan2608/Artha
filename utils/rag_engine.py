import chromadb
from chromadb.utils import embedding_functions

# Initialize a local in-memory ChromaDB client.
_chroma_client = chromadb.Client()

# Initialize the embedding model.
_embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

COLLECTION_NAME = "session_documents"

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Splits a continuous string of text into overlapping chunks."""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
        
    return chunks

def index_document(doc_id: str, parsed_data: dict) -> None:
    """
    Chunks and loads parsed document data into the vector database.
    """
    if parsed_data.get("type") == "error" or not parsed_data.get("content"):
        return

    collection = _chroma_client.get_or_create_collection(
        name=COLLECTION_NAME, 
        embedding_function=_embed_fn
    )
    
    doc_type = parsed_data["type"]
    raw_content = parsed_data["content"]
    text_chunks = []

    # Handle Tabular Data (xlsx, csv)
    if doc_type in ["xlsx", "csv"] and isinstance(raw_content, dict):
        for sheet_name, rows in raw_content.items():
            for row in rows:
                row_values = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                if row_values:
                    row_str = " | ".join(row_values)
                    text_chunks.append(f"[Sheet: {sheet_name}] {row_str}")
                    
    # Handle Standard Text (pdf, docx, pptx, txt)
    elif isinstance(raw_content, str):
        text_chunks = chunk_text(raw_content)

    if not text_chunks:
        return

    chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(text_chunks))]
    metadatas = [{"source": doc_id, "type": doc_type} for _ in text_chunks]

    collection.add(
        documents=text_chunks,
        metadatas=metadatas,
        ids=chunk_ids
    )

def query_documents(query: str, n_results: int = 5) -> list[str]:
    """
    Searches the vector database for text chunks matching the query.
    """
    try:
        collection = _chroma_client.get_collection(
            name=COLLECTION_NAME, 
            embedding_function=_embed_fn
        )
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        if results and results.get("documents") and results["documents"][0]:
            return results["documents"][0]
            
        return []
    except ValueError:
        # Collection does not exist yet
        return []
    except Exception:
        return []
