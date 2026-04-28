import json
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Global variables to hold the vectorizer and TF-IDF matrix
_vectorizer = None
_tfidf_matrix = None
_policies = []

def init_rag(filepath: str = "policies.json"):
    """
    Initializes the in-memory RAG by loading policies and fitting TF-IDF.
    """
    global _vectorizer, _tfidf_matrix, _policies
    
    # Resolve absolute path for policies.json
    base_dir = os.path.dirname(__file__)
    full_path = os.path.join(base_dir, filepath)
    
    if not os.path.exists(full_path):
        print(f"Warning: Policies file not found at {full_path}")
        return

    with open(full_path, "r", encoding="utf-8") as f:
        _policies = json.load(f)

    # Prepare texts for TF-IDF (combining topic and policy)
    texts = [f"{p['topic']} {p['policy']}" for p in _policies]
    
    _vectorizer = TfidfVectorizer(stop_words='english')
    _tfidf_matrix = _vectorizer.fit_transform(texts)

def retrieve_policy(query: str, top_k: int = 2) -> list:
    """
    Retrieves the top_k most relevant policies for the given query.
    """
    if _vectorizer is None or _tfidf_matrix is None or not _policies:
        return []

    query_vec = _vectorizer.transform([query])
    similarities = cosine_similarity(query_vec, _tfidf_matrix).flatten()
    
    # Get top k indices
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    # Filter out low similarity scores
    results = []
    for idx in top_indices:
        if similarities[idx] > 0.05: # Minimum threshold
            results.append({
                "topic": _policies[idx]["topic"],
                "policy": _policies[idx]["policy"],
                "score": float(similarities[idx])
            })
    
    return results

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
