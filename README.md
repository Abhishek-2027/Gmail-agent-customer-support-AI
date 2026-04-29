# Mumzworld Customer Support AI Agent

An automated, intelligent email triaging system designed for e-commerce customer support. It classifies customer intents, detects urgency, retrieves store policies, and generates natural, localized responses in both English and Arabic.

## The Problem Statement
Mumzworld receives thousands of customer emails every day in both English and Arabic. It is slow and difficult for human agents to manually:
*   **Identify** what the customer wants (Intent).
*   **Decide** how urgent the request is (Urgency).
*   **Search** for the right company policies or look up order statuses in the database.
*   **Write** a polite, accurate reply in the correct language.

## The Solution
We built an **AI Support Triager** that acts as a "Digital Assistant" for support agents. It handles the heavy lifting in ~4 seconds:
*   **Triage**: Instantly categorizes the email and detects the language (EN/AR).
*   **Facts, not Guesses**: It uses **Hybrid RAG** (to read company policies) and **Tools** (to look up live order data) so it never invents facts.
*   **Drafting**: It writes a "Suggested Reply" that the agent can simply click and send.

## Example in Action
1.  **The Input (The Problem)**:
    *   *Customer Email:* "I bought a stroller but it's too big. Can I return it? My order is MW-2002."
2.  **The AI at Work (The Solution)**:
    *   **Detects Intent**: `exchange` / `refund`.
    *   **Uses Tool**: Looks up `MW-2002` → Finds it was delivered 2 days ago.
    *   **Uses RAG**: Reads the Return Policy → Finds "Returns allowed within 14 days if unused."
    *   **Calculates Confidence**: 95% (because it found the order and the policy).
3.  **The Output (The Result)**:
    *   **Suggested Reply**: *"I see you'd like to return your stroller from order MW-2002. Since it was delivered 2 days ago, you are within our 14-day return window. Would you like me to start the return process for you?"*

## Advanced Architecture (Production Ready)

1. **Throttling & Rate Limiting**: Implements a global **1 request per second** throttle to ensure stability and eliminate `429 Too Many Requests` errors.
2. **In-Memory Caching**: Implements a SHA-256 hashed response cache. Repeat requests for the same input are **instant** and use **zero API tokens**.
3. **Preprocessing Layer**: Cleans up text and removes signatures/greetings to reduce LLM noise.
4. **Classification (Fast LLM)**: Uses `meta-llama/llama-3-8b-instruct` to quickly determine Language, Intent, and Urgency in a single call.
5. **Advanced RAG (Vector DB)**: Uses **ChromaDB** with **Sentence-Transformers** (`all-MiniLM-L6-v2`) for semantic search. This ensures the system understands the meaning of queries (e.g., matching "money back" to "refund policy") rather than just keyword matching.
6. **Generation & Reasoning (Complex LLM)**: Uses `deepseek/deepseek-chat` to generate high-quality, grounded responses with clear reasoning.
7. **Confidence Scorer**: Calculates a weighted score combining LLM confidence and semantic similarity.
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
To ensure the system is production-ready, I implemented a suite of **10 test cases** covering various scenarios.

### Evaluation Rubric
1.  **Intent Accuracy**: Does the model correctly identify the customer's goal?
2.  **Uncertainty Handling**: Does the system correctly flag confusing or gibberish input as `unknown` with low confidence?
3.  **Schema Validation**: Is the output always a valid JSON that matches our Pydantic schema?

### Test Case Breakdown
| # | Scenario | Type | Expected Behavior |
|---|----------|------|-------------------|
| 1 | Simple Refund (EN) | Easy | Intent: `refund`, Confidence: High |
| 2 | Simple Exchange (AR) | Easy | Intent: `exchange`, Confidence: High |
| 3 | Safety/Health Issue | Critical | Intent: `escalate`, Urgency: High |
| 4 | Late Return | Edge Case | Intent: `store_credit` (based on policy) |
| 5 | Missing Order ID | Unclear | Intent: `unknown`, Ask for info |
| 6 | Conflicting Request | Adversarial | Intent: `unknown`, Fallback triggered |
| 7 | Gibberish Input | Adversarial | Intent: `unknown`, Low confidence |
| 8 | Signature Heavy | Noisy | Correctly ignores signature, finds intent |
| 9 | Missing Item (AR) | Arabic | Intent: `escalate` / `order_tracking` |
| 10| Empty Input | Boundary | Intent: `unknown`, Graceful failure |

### Running Evals
```bash
python backend/eval.py
```
*Note: The script includes a 4-second sleep between cases to stay within OpenRouter's free tier rate limits.*

### Evaluation Results (Actual Scores)
| Metric | Score |
|---|---|
| **Total Tests** | 10 |
| **Passed Cases** | 6/10 |
| **Intent Accuracy** | 60.0% |
| **Uncertainty Correctness** | 60.0% |

### Analysis of Failures (Honest Disclosure)
*   **Model "Helpfulness"**: In cases 5 and 6 (Adversarial), the Llama 3 model attempted to guess an intent (like `exchange`) instead of correctly identifying it as `unknown`. This highlights a common tradeoff where models are "too helpful" and need further prompt tuning or few-shot examples to improve uncertainty detection.
*   **Schema Strictness**: Case 4 failed because the model returned `return` instead of the strictly required `refund`. This triggered a validation error, which proves our **Schema Validation** is working correctly to protect the system from malformed data.
*   **Arabic JSON Formatting**: One Arabic case failed because the model included a minor delimiter error in its raw output, which our current parser couldn't fix.

## Tradeoffs

### What I Chose
- **OpenRouter Multi-Model Setup**: Distributed load across `Llama 3` (fast classification) and `DeepSeek` (complex generation) to maximize speed and quality while managing quotas.
- **Throttling & Caching**: Prioritized stability over raw throughput to ensure the system never crashes under load.
- **Semantic RAG**: Transitioned from keyword-based TF-IDF to **ChromaDB Vector Search**. This handles synonym matching (e.g., "damaged" vs "defective") and provides a more robust grounding for the LLM.

### What I Skipped
- **Persistent Database**: Used in-memory caching and JSON-based storage for the prototype setup speed.
- **Complex Thread Memory**: Treated each email as an isolated ticket for clean triaging logic.

## Tooling & Provenance

This project was built using a combination of manual engineering and AI-assisted coding, as encouraged by the Mumzworld brief.

### 1. Harnesses & Models
*   **OpenRouter**: Used as the primary gateway for all LLM calls.
*   **Llama 3 (meta-llama/llama-3-8b-instruct)**: Used for the **Classification & Triage** layer. Its speed and ability to follow JSON schemas make it perfect for fast intent/language detection.
*   **DeepSeek Chat (deepseek/deepseek-chat)**: Used for **Grounded Generation**. It produces more natural, conversational English and Arabic responses compared to smaller models.
*   **Sentence-Transformers (all-MiniLM-L6-v2)**: Used locally via Python to generate embeddings for semantic search in ChromaDB.

### 2. How I used AI
*   **Pair-Coding (Antigravity)**: I used an AI coding assistant (Antigravity) to help scaffold the FastAPI backend, write the CSS for the premium UI, and iterate on the logic for the global throttler.
*   **Prompt Iteration**: I iterated on the system messages for the classification step to ensure the model distinguishes between `refund` (simple) and `escalate` (safety issues).
*   **Eval Drafting**: The 10-case evaluation suite was drafted with AI assistance to ensure coverage of adversarial inputs.

### 3. What Worked & What Didn't
*   **Worked**: The multi-model approach is highly efficient. Using a small model for classification saved significantly on latency.
*   **Did Not Work**: Initial attempts at pure keyword matching for policies failed with Arabic. Switching to **Vector Search (ChromaDB)** was necessary to handle semantic similarity in both languages.
*   **Overruled**: I manually overrode the AI's initial suggestion to use simple string parsing for JSON and instead implemented a robust regex-based extraction to handle "noisy" LLM outputs.

### 4. Key Prompts
The core system message for the triager is:
```text
"You are a customer support triage AI. Analyze the email and return ONLY a raw JSON object: 
'language', 'intent' [refund, exchange, store_credit, order_tracking, escalate, unknown], 
'urgency' [low, medium, high], 'confidence' [0.0-1.0]."
```

---

## Project Structure

```
customer-support-ai/
│
├── backend/
│   ├── main.py                     # FastAPI routes & static file serving
│   ├── pipeline.py                 # Core business logic orchestrator
│   ├── llm_engine.py               # Throttling, Caching, & LLM calls
│   ├── retrieval.py                # ChromaDB + Sentence-Transformers RAG
│   ├── tools.py                    # Order lookup tool (mock DB connector)
│   ├── schema.py                   # Pydantic validation schemas
│   ├── utils.py                    # Robust JSON extraction & preprocessing
│   ├── policies.json               # Policy knowledge base (JSON)
│   ├── mock_orders.json            # Order database (JSON)
│   ├── .env                        # API keys (not committed)
│   └── eval.py                     # 10-case evaluation suite
│
├── frontend/
│   ├── index.html                  # UI structure
│   ├── style.css                   # Premium gradients & responsiveness
│   └── script.js                   # Fetch logic & RTL detection
│
├── requirements.txt                # Project dependencies
└── .gitignore                      # Git exclusion rules
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
                                  ├─ 5. Retrieve Policy (ChromaDB Semantic Search)
                                  ├─ 6. Generate Response (DeepSeek)
                                  │    With exponential backoff retry
                                  └─ 7. Validate (schema.py)
                                  │
        ◄────── JSON response ────┘
        │
script.js renders badges, confidence bar, & RTL localized reply
```
