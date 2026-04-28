import os
import json
import httpx
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
FAST_MODEL = os.getenv("FAST_MODEL", "gemini-2.5-flash")           # Gemini
COMPLEX_MODEL = os.getenv("COMPLEX_MODEL", "openai/gpt-oss-120b:free")  # OpenRouter


# ---------------------------------------------------------------------------
# PROVIDER 1: Gemini REST API  (used for fast structured classification)
# ---------------------------------------------------------------------------

async def call_gemini(prompt: str, system_prompt: str, model: str, require_json: bool = False) -> str:
    """
    Calls Gemini REST API with exponential-backoff retry on 429/503.
    Best for: structured JSON classification (small, fast, reliable).
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in .env")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    payload: dict = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": prompt}]}]
    }
    if require_json:
        payload["generationConfig"] = {"responseMimeType": "application/json"}

    max_retries, base_delay = 5, 10

    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                r = await client.post(url, json=payload, timeout=60.0)
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [429, 503] and attempt < max_retries - 1:
                    wait = base_delay * (2 ** attempt)
                    print(f"[Gemini] {e.response.status_code} — retry in {wait}s (attempt {attempt+1})")
                    await asyncio.sleep(wait)
                    continue
                raise
            except (KeyError, IndexError):
                raise Exception(f"Unexpected Gemini response: {r.text[:200]}")


# ---------------------------------------------------------------------------
# PROVIDER 2: OpenRouter API  (used for creative response generation)
# ---------------------------------------------------------------------------

async def call_openrouter(prompt: str, system_prompt: str, model: str) -> str:
    """
    Calls OpenRouter API with exponential-backoff retry on 429/503/528.
    Best for: creative writing, Arabic generation, longer responses.
    Falls back to Gemini if all retries fail.
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set in .env")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Mumzworld CS Agent",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt + "\n\nReturn ONLY valid raw JSON. No markdown."},
            {"role": "user", "content": prompt}
        ]
    }

    max_retries, base_delay = 4, 5

    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers, json=payload, timeout=60.0
                )
                r.raise_for_status()
                data = r.json()
                if "choices" in data:
                    return data["choices"][0]["message"]["content"]
                raise Exception(f"Unexpected OpenRouter response: {data}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [429, 503, 528] and attempt < max_retries - 1:
                    wait = base_delay * (2 ** attempt)
                    print(f"[OpenRouter] {e.response.status_code} — retry in {wait}s (attempt {attempt+1})")
                    await asyncio.sleep(wait)
                    continue
                # If OpenRouter exhausted, fall back to Gemini for generation too
                print(f"[OpenRouter] Error {e.response.status_code}: {e.response.text}. Falling back to Gemini...")
                return await call_gemini(prompt, system_prompt, "gemini-2.5-flash", require_json=True)


# ---------------------------------------------------------------------------
# Step 2+3+4: Language Detection + Intent + Urgency  →  GEMINI (fast)
# ---------------------------------------------------------------------------

async def detect_language_and_urgency_and_intent(email_text: str) -> Dict[str, Any]:
    """
    Uses OpenRouter (FAST_MODEL) for rapid structured JSON classification.
    Single API call returns: language, intent, urgency, confidence.
    """
    system_prompt = (
        "You are an expert customer support triaging AI.\n"
        "Analyse the email and return ONLY a raw JSON object with these 4 keys:\n"
        '  "language": "en" or "ar"\n'
        '  "intent": one of [refund, exchange, store_credit, escalate, unknown]\n'
        '  "urgency": one of [low, medium, high]\n'
        '  "confidence": float 0.0-1.0  (MUST be < 0.5 when intent is unknown)\n'
        "No markdown, no explanation — just the JSON."
    )
    # Using call_openrouter instead of call_gemini to avoid 429s
    response = await call_openrouter(email_text, system_prompt, FAST_MODEL)

    from utils import extract_json_from_llm_response
    try:
        return json.loads(extract_json_from_llm_response(response))
    except Exception:
        return {"language": "en", "intent": "unknown", "urgency": "low", "confidence": 0.0}


# ---------------------------------------------------------------------------
# Step 7: Response Generation  →  OPENROUTER (separate quota pool)
# ---------------------------------------------------------------------------

async def generate_response(
    email_text: str,
    intent: str,
    urgency: str,
    language: str,
    context: str,
    fallback_mode: bool = False
) -> Dict[str, str]:
    """
    Uses OpenRouter (COMPLEX_MODEL) for creative, grounded response generation.
    Writes in customer's detected language (natural Arabic for GCC, English otherwise).
    Automatically falls back to Gemini if OpenRouter is unavailable.
    """
    system_prompt = (
        f"You are an empathetic customer support agent for Mumzworld (e-commerce for mothers in the Middle East).\n"
        f"LANGUAGE RULE: Write 'suggested_reply' in language='{language}'. "
        f"If language='ar', use natural GCC Arabic — NOT a literal translation.\n\n"
        f"Intent: {intent} | Urgency: {urgency}\n\n"
        "RULES:\n"
        "1. Return ONLY a raw JSON object with keys: 'reasoning' (English, brief) and 'suggested_reply' (target language).\n"
        "2. Do NOT invent policies. Use ONLY the Context below.\n"
        f"3. If fallback_mode=True, ask politely for clarification — do NOT guess intent.\n\n"
        f"Context (Policies):\n{context}"
    )
    prompt = f"Customer Email:\n{email_text}\n\nfallback_mode: {fallback_mode}"

    response = await call_openrouter(prompt, system_prompt, COMPLEX_MODEL)

    from utils import extract_json_from_llm_response
    try:
        return json.loads(extract_json_from_llm_response(response))
    except Exception as e:
        return {
            "reasoning": f"LLM parse error: {e}",
            "suggested_reply": "We're sorry for the inconvenience. Could you please clarify your request?"
        }
