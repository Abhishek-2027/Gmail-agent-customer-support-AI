# Mumzworld Customer Support AI Agent

An automated, intelligent email triaging system designed for e-commerce customer support. It classifies customer intents, detects urgency, retrieves store policies, and generates natural, localized responses in both English and Arabic.

## Problem Statement
E-commerce platforms like Mumzworld receive massive volumes of free-text customer emails daily. These emails often lack structure, jump between topics, or contain high noise (signatures, greetings). Human agents spend a significant amount of time just reading, categorizing, and looking up policies before they can even write a reply. 

This AI agent automates the first layer of support. By securely categorizing intents, accurately scoring confidence, and directly fetching internal policies via RAG, it provides human agents with a pre-written, highly accurate draft response. Crucially, it handles uncertainty well—if an email is confusing, it will explicitly flag it as `unknown` with low confidence and draft a response asking for clarification.

## Architecture

1. **Preprocessing Layer**: Cleans up text and removes signatures/greetings to reduce LLM noise.
2. **Classification (Fast LLM)**: Uses a lightweight, fast model to quickly determine Language, Intent, and Urgency.
3. **Retrieval-Augmented Generation (RAG)**: A lightweight, TF-IDF vector-based search over an internal `policies.json`. It finds the specific policy rules relevant to the detected intent and customer text.
4. **Generation & Reasoning (Complex LLM)**: A larger, high-capability model takes the raw email, the classified metadata, and the retrieved policy context. It generates the final response in the detected language (natural Arabic or English) and explains *why* it chose that response.
5. **Confidence Scorer**: Calculates a weighted score combining the LLM's classification confidence and the RAG semantic similarity score.
6. **JSON Validation Layer**: A strict Pydantic layer ensures the API only returns structurally flawless JSON to the frontend.

## Setup Instructions (Run in < 5 minutes)

### Prerequisites
- Python 3.10+
- An API key from [Google AI Studio (Gemini)](https://aistudio.google.com/)

### Installation
1. Navigate to the directory:
   ```bash
   cd customer-support-ai
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```
3. Set up your environment variables:
   - Rename `.env.example` to `.env`.
   - Add your Gemini API key.
   ```bash
   GEMINI_API_KEY="AIzaSy..."
   ```

### Running the App
1. Start the FastAPI backend:
   ```bash
   uvicorn backend.main:app --reload
   ```
2. Open the frontend:
   Simply open `frontend/index.html` in your web browser. 

## Evaluations (eval.py)
We built an automated evaluation script that tests 10 varied scenarios, including:
- Easy straightforward requests (English & Arabic).
- Edge cases (late returns).
- Safety escalations.
- Adversarial conflicting emails.
- Noise-heavy and gibberish emails.

**To run the evaluations:**
```bash
python backend/eval.py
```
*Note: Due to the non-deterministic nature of LLMs, results may slightly vary per run, but the architecture is designed to consistently handle uncertainty.*

## Tradeoffs

### What I Chose
- **Multi-Model Architecture via Gemini API**: I opted for a two-model setup. `gemini-2.5-flash` handles the simple classification steps (saving time/tokens), while `gemini-2.5-pro` handles the nuance of Arabic generation and policy reasoning. 
- **TF-IDF for RAG**: Instead of bringing in heavy dependencies like `sentence-transformers` or `PyTorch` for a 5-hour prototype, I used `scikit-learn`'s TF-IDF. For a small `policies.json` file, exact keyword and semantic overlap works exceptionally well and installs instantly.
- **Explicit Uncertainty Fallbacks**: Rather than letting the LLM guess when it's confused, the `pipeline.py` intercepts low-confidence or `unknown` intents and forces the generation step into a `fallback_mode`, guaranteeing it asks the user for clarification.

### What I Skipped
- **Vector Database**: Used in-memory `numpy` arrays instead of Pinecone/Qdrant to meet the < 5 minute setup constraint.
- **Complex Thread Memory**: Skipped multi-turn conversation memory for this initial triage prototype, treating each email as an isolated ticket.

## Tooling & Provenance
- **Harness & Models**: This project was built utilizing the Google Gemini REST API. The default models chosen are `gemini-2.5-flash` (for fast classification) and `gemini-2.5-pro` (for complex generation and Arabic support). These models are highly capable and available via Google AI Studio.
- **AI Agent Used**: I utilized an AI coding assistant (similar to KiloCode / OpenCode) to construct the repository scaffold, generate boilerplate FastAPI code, write the frontend CSS styling, and draft the initial evaluation test cases based on my architectural prompts.
- **Manual Intervention**: I manually enforced the Pydantic JSON validation flow, tuned the confidence scoring algorithm mathematically in `pipeline.py`, and structured the Arabic/English edge case evals.

---

## Project Structure

```
customer-support-ai/
│
├── backend/                        # All server-side logic
│   ├── venv/                       # Python virtual environment (not committed)
│   ├── .env                        # API keys and model config (not committed)
│   ├── requirements.txt            # Python dependencies
│   │
│   ├── main.py                     # FastAPI app — defines /analyze and /health routes
│   ├── schema.py                   # Pydantic models — strict input/output validation
│   ├── pipeline.py                 # Core orchestrator — runs all pipeline steps in order
│   ├── llm_engine.py               # Dual LLM provider — Gemini (classify) + OpenRouter (generate)
│   ├── retrieval.py                # TF-IDF RAG — vectorizes policies, retrieves context
│   ├── utils.py                    # Email preprocessing + JSON extraction helpers
│   ├── policies.json               # Internal knowledge base (store policies)
│   └── eval.py                     # Automated evaluation — 10 test cases, accuracy scoring
│
├── frontend/                       # Browser UI
│   ├── index.html                  # HTML structure — layout, cards, textarea, button
│   ├── style.css                   # Premium CSS — gradients, badges, confidence bar
│   └── script.js                   # JS logic — fetch API, render results, RTL detection
│
└── README.md                       # This file
```

---

## How Every File Connects — Full Data Flow

### Step-by-Step: From Browser to AI and Back

#### 1. User Opens `frontend/index.html`
The browser loads all three frontend files together:
- `index.html` defines the visual skeleton: textarea, submit button, output cards
- `style.css` styles everything — confidence bar, badge colors, animated spinner
- `script.js` attaches a click listener and handles all interactivity

#### 2. User Clicks Submit → `frontend/script.js`
1. Reads the textarea value
2. Starts an animated step counter (*"Detecting language... → Classifying intent..."*)
3. Launches a `fetch()` POST to `http://localhost:8000/analyze` with a 90s `AbortController` timeout
4. Renders the JSON result across the output cards on success

```
Browser → POST http://localhost:8000/analyze
          Body: { "email_text": "..." }
```

#### 3. API Receives Request → `backend/main.py`
1. FastAPI validates the incoming body using `EmailRequest` from `schema.py` (rejects missing fields with 422)
2. Calls `run_pipeline(email_text)` from `pipeline.py`
3. Wraps the result in `OutputResponse` from `schema.py` — fails explicitly if any field is wrong type or out of range

#### 4. The AI Pipeline → `backend/pipeline.py`

**Preprocessing** (`utils.py`):
- Strips signatures, greetings, and noise using regex
- Returns `intent: unknown, confidence: 0.0` immediately if email is empty

**Classification** (`llm_engine.py` → Gemini 2.5 Flash):
- `detect_language_and_urgency_and_intent()` sends the cleaned email to Gemini
- Returns structured JSON: `language`, `intent`, `urgency`, `confidence`
- Uses Gemini's native JSON mode for guaranteed schema compliance

**Policy Retrieval** (`retrieval.py`):
- `retrieve_policy()` uses TF-IDF cosine similarity to search `policies.json`
- Query = `"{intent} {email_text}"` for best semantic match
- Returns top-2 policies with similarity scores

**Confidence Scoring** (`pipeline.py`):
```
final_confidence = (classification_conf × 0.7) + (rag_score × 0.3)
```
- Hard-capped at 0.4 when intent is unknown — prevents false certainty

**Response Generation** (`llm_engine.py` → OpenRouter Gemma):
- `generate_response()` sends email + intent + context to OpenRouter
- If `fallback_mode=True` → forces a polite clarification request
- Writes reply in detected language (natural GCC Arabic or English)
- If OpenRouter fails → auto-fallback to Gemini Flash

#### 5. Output Validation → `backend/schema.py`
Before returning to the browser, `OutputResponse` strictly validates:
- `intent` must be one of 5 exact literals
- `confidence` must be float between 0.0 and 1.0
- All fields must be present and non-empty
- Failures raise HTTP 500 with explicit error detail — never silent

#### 6. UI Renders Results → `frontend/script.js`
- `intent` → colored badge (purple for known, grey for unknown)
- `urgency` → colored badge (green/amber/red)
- `confidence` → animated progress bar (color changes at 50% and 80% thresholds)
- `suggested_reply` → auto-detects Arabic script and sets `direction: rtl`

#### 7. Evaluation → `backend/eval.py`
Runs standalone, calls `run_pipeline()` directly with 10 test cases and reports:
- Intent accuracy %
- Uncertainty correctness %
- Per-test PASS/FAIL with confidence scores

---

### Complete Request Lifecycle

```
User types email in browser
        │
        ▼
script.js  ──POST /analyze──►  main.py
                                  │
                                  ├─ validate input       (schema.py)
                                  ├─ preprocess email     (utils.py)
                                  ├─ classify             (llm_engine.py → Gemini Flash)
                                  │    language + intent + urgency + confidence
                                  ├─ retrieve policy      (retrieval.py → TF-IDF)
                                  │    cosine similarity on policies.json
                                  ├─ score confidence     (pipeline.py)
                                  │    weighted: 70% LLM + 30% RAG
                                  ├─ generate reply       (llm_engine.py → OpenRouter Gemma)
                                  │    fallback: Gemini Flash if OpenRouter fails
                                  └─ validate output      (schema.py)
                                  │
        ◄────── JSON response ────┘
        │
script.js renders intent, urgency, confidence bar, reasoning, reply (with RTL if Arabic)
```

