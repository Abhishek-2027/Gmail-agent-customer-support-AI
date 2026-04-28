# Mumzworld Customer Support AI Agent

An automated, intelligent email triaging system designed for e-commerce customer support. It classifies customer intents, detects urgency, retrieves store policies, and generates natural, localized responses in both English and Arabic.

## Problem Statement
E-commerce platforms like Mumzworld receive massive volumes of free-text customer emails daily. Human agents spend a significant amount of time just reading, categorizing, and looking up policies before they can even write a reply. 

This AI agent automates the first layer of support. By securely categorizing intents, accurately scoring confidence, and directly fetching internal policies via RAG, it provides human agents with a pre-written draft response. It handles uncertainty well—if an email is confusing, it will explicitly flag it as `unknown` and ask for clarification.

## Advanced Architecture (Production Ready)

1. **Throttling & Rate Limiting**: Implements a global **1 request per second** throttle to ensure stability and eliminate `429 Too Many Requests` errors.
2. **In-Memory Caching**: Implements a SHA-256 hashed response cache. Repeat requests for the same input are **instant** and use **zero API tokens**.
3. **Preprocessing Layer**: Cleans up text and removes signatures/greetings to reduce LLM noise.
4. **Classification (Fast LLM)**: Uses `meta-llama/llama-3-8b-instruct` to quickly determine Language, Intent, and Urgency in a single call.
5. **Retrieval-Augmented Generation (RAG)**: A lightweight, TF-IDF vector-based search over internal policies to find rules relevant to the customer's request.
6. **Generation & Reasoning (Complex LLM)**: Uses `deepseek/deepseek-chat` to generate high-quality, grounded responses with clear reasoning.
7. **Confidence Scorer**: Calculates a weighted score combining LLM confidence and RAG similarity.
8. **Exponential Backoff**: Implements 3 retries (1s, 2s, 4s) to handle transient API issues.

## Setup Instructions

### Prerequisites
- Python 3.10+
- An API key from [OpenRouter](https://openrouter.ai/)

### Installation
1. Navigate to the directory:
   ```bash
   cd customer-support-ai
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   # or
   .\venv\Scripts\activate   # Windows
   
   pip install -r requirements.txt
   ```
3. Set up your environment variables in `.env`:
   ```bash
   OPENROUTER_API_KEY="sk-or-v1-..."
   FAST_MODEL="meta-llama/llama-3-8b-instruct"
   COMPLEX_MODEL="deepseek/deepseek-chat"
   ```

### Running the App
1. Start the FastAPI backend:
   ```bash
   uvicorn backend.main:app --reload
   ```
2. Open the frontend:
   Simply open `frontend/index.html` in your web browser.

## Evaluations (eval.py)
Automated testing of 10 varied scenarios (English/Arabic requests, safety escalations, adversarial inputs).
```bash
python backend/eval.py
```

## Tradeoffs

### What I Chose
- **OpenRouter Multi-Model Setup**: Distributed load across `Llama 3` (fast classification) and `DeepSeek` (complex generation) to maximize speed and quality while managing quotas.
- **Throttling & Caching**: Prioritized stability over raw throughput to ensure the system never crashes under load.
- **TF-IDF for RAG**: Used `scikit-learn` for instant, dependency-light semantic search that works perfectly for policy knowledge bases.

### What I Skipped
- **Persistent Database**: Used in-memory caching and JSON-based storage for the prototype setup speed.
- **Complex Thread Memory**: Treated each email as an isolated ticket for clean triaging logic.

## Tooling & Provenance
- **Harness & Models**: Built using **OpenRouter API** with Llama 3 and DeepSeek models.
- **AI Agent Used**: Leveraged an AI coding assistant for scaffolding, CSS styling, and initial test drafting.
- **Manual Engineering**: Manually implemented the global throttler, hashed caching system, weighted confidence algorithm, and RTL support.

---

## Project Structure

```
customer-support-ai/
│
├── backend/
│   ├── main.py                     # FastAPI routes & entry point
│   ├── pipeline.py                 # Core business logic orchestrator
│   ├── llm_engine.py               # Throttling, Caching, Retry, & LLM calls
│   ├── retrieval.py                # TF-IDF RAG implementation
│   ├── schema.py                   # Pydantic validation schemas
│   ├── utils.py                    # Robust JSON extraction & preprocessing
│   ├── policies.json               # Policy knowledge base
│   └── eval.py                     # 10-case evaluation suite
│
├── frontend/
│   ├── index.html                  # UI structure
│   ├── style.css                   # Premium gradients & responsiveness
│   └── script.js                   # Fetch logic & RTL detection
│
└── requirements.txt                # Unified dependencies
```

## Data Flow Diagram

```
User types email in browser
        │
        ▼
script.js  ──POST /analyze──►  main.py
                                  │
                                  ├─ 1. Rate Limiting Check (1 req/s)
                                  ├─ 2. Cache Check (Hashed Prompt)
                                  ├─ 3. Preprocess (utils.py)
                                  ├─ 4. Classify (Llama 3)
                                  │    Language + Intent + Urgency
                                  ├─ 5. Retrieve Policy (TF-IDF)
                                  ├─ 6. Generate Response (DeepSeek)
                                  │    With exponential backoff retry
                                  └─ 7. Validate (schema.py)
                                  │
        ◄────── JSON response ────┘
        │
script.js renders badges, confidence bar, & RTL localized reply
```
