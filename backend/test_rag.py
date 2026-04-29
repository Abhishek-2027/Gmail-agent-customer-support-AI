from retrieval import init_rag, retrieve_policy, get_context_string
import os

def test_semantic_search():
    print("--- Initializing Semantic RAG ---")
    # Policies file is in the same directory as retrieval.py
    init_rag("policies.json")
    
    test_queries = [
        "How do I get my money back?",            # Semantic match to 'Refunds'
        "Can I change this for a different color?", # Semantic match to 'Exchanges'
        "My baby got a rash from the cream",       # Semantic match to 'Escalation - Safety'
        "I didn't receive one of my items",        # Semantic match to 'Missing Items'
        "Where is my credit?",                      # Semantic match to 'Store Credit'
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = retrieve_policy(query, top_k=1)
        if results:
            res = results[0]
            print(f"Match Found: {res['topic']} (Score: {res['score']:.2f})")
            print(f"Policy: {res['policy'][:100]}...")
        else:
            print("No match found.")

if __name__ == "__main__":
    test_semantic_search()
