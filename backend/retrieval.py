import json
import os

# Disable ChromaDB telemetry before import
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.utils import embedding_functions

# Global variables to hold the Chroma collection
_collection = None
_policies = []

def init_rag(filepath: str = "policies.json"):
    """
    Initializes the ChromaDB vector store by loading policies and embedding them.
    """
    global _collection, _policies
    
    # Resolve absolute path for policies.json
    base_dir = os.path.dirname(__file__)
    full_path = os.path.join(base_dir, filepath)
    
    if not os.path.exists(full_path):
        print(f"Warning: Policies file not found at {full_path}")
        return

    with open(full_path, "r", encoding="utf-8") as f:
        _policies = json.load(f)

    # Initialize Ephemeral Chroma Client
    from chromadb.config import Settings
    client = chromadb.Client(Settings(anonymized_telemetry=False))
    
    # Use Sentence Transformers for local semantic embeddings
    # 'all-MiniLM-L6-v2' is fast, lightweight, and effective for support queries
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    # Create or reset collection
    collection_name = "mumzworld_policies"
    try:
        client.delete_collection(name=collection_name)
    except:
        pass
        
    _collection = client.create_collection(name=collection_name, embedding_function=ef)

    # Prepare data for Chroma
    documents = [f"{p['topic']}: {p['policy']}" for p in _policies]
    metadatas = [{"topic": p["topic"], "id": p.get("id", f"p_{i}")} for i, p in enumerate(_policies)]
    ids = [p.get("id", f"p_{i}") for i, p in enumerate(_policies)]

    # Add to collection
    _collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

def retrieve_policy(query: str, top_k: int = 2) -> list:
    """
    Retrieves the top_k most relevant policies for the given query using semantic search.
    """
    if _collection is None:
        return []

    results = _collection.query(
        query_texts=[query],
        n_results=top_k
    )

    # Chroma returns results in a nested structure
    # distances are also returned. For cosine sim, lower is better (0.0 = identical).
    # We'll convert distance to a similarity score for the pipeline logic.
    retrieved = []
    if results['documents']:
        for i in range(len(results['documents'][0])):
            distance = results['distances'][0][i]
            # Convert distance to similarity (rough approximation: 1 / (1 + distance))
            similarity = 1.0 / (1.0 + distance)
            
            retrieved.append({
                "topic": results['metadatas'][0][i]['topic'],
                "policy": results['documents'][0][i].split(": ", 1)[1] if ": " in results['documents'][0][i] else results['documents'][0][i],
                "score": float(similarity)
            })

    # Filter out low similarity scores (threshold adjusted for embeddings)
    return [r for r in retrieved if r['score'] > 0.4]

def get_context_string(results: list) -> str:
    """
    Formats the retrieval results into a readable context string.
    """
    if not results:
        return "No specific policies found."
    
    context_parts = []
    for r in results:
        context_parts.append(f"- {r['topic']}: {r['policy']}")
    return "\n".join(context_parts)
