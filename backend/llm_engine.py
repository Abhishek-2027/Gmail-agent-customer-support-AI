import os
import json
import httpx
import asyncio
import time
import hashlib
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
FAST_MODEL = os.getenv("FAST_MODEL", "meta-llama/llama-3-8b-instruct")
COMPLEX_MODEL = os.getenv("COMPLEX_MODEL", "deepseek/deepseek-chat")

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleCache:
    """In-memory cache for LLM responses."""
    def __init__(self):
        self.cache = {}

    def _generate_key(self, prompt: str, system_prompt: str, model: str) -> str:
        combined = f"{model}:{system_prompt}:{prompt}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def get(self, prompt: str, system_prompt: str, model: str) -> Optional[str]:
        key = self._generate_key(prompt, system_prompt, model)
        return self.cache.get(key)

    def set(self, prompt: str, system_prompt: str, model: str, response: str):
        key = self._generate_key(prompt, system_prompt, model)
        self.cache[key] = response

class Throttler:
    """Ensures at least 1 second between requests."""
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.last_call_time = 0
        self.lock = asyncio.Lock()

    async def wait(self):
        async with self.lock:
            elapsed = time.time() - self.last_call_time
            if elapsed < self.delay:
                wait_time = self.delay - elapsed
                logger.info(f"Throttling active: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            self.last_call_time = time.time()

# Global instances
llm_cache = SimpleCache()
throttler = Throttler(delay=1.0)

async def call_llm(prompt: str, system_prompt: str, model: str) -> str:
    """
    Unified caller for OpenRouter with Throttling, Caching, and Exponential Backoff.
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set in .env")

    # 1. Check Cache
    cached_res = llm_cache.get(prompt, system_prompt, model)
    if cached_res:
        logger.info(f"Cache hit for model {model}")
        return cached_res

    # 2. Wait for Throttler
    await throttler.wait()

    # 3. API Call with Retries
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

    # Retries: 1s, 2s, 4s
    backoff_times = [1, 2, 4]
    
    async with httpx.AsyncClient() as client:
        for attempt, wait_time in enumerate(backoff_times + [0]): # last 0 is dummy for loop control
            try:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers, 
                    json=payload, 
                    timeout=60.0
                )
                r.raise_for_status()
                data = r.json()
                
                if "choices" in data:
                    content = data["choices"][0]["message"]["content"]
                    # Store in cache
                    llm_cache.set(prompt, system_prompt, model, content)
                    return content
                
                raise Exception(f"Unexpected response structure: {data}")

            except httpx.HTTPStatusError as e:
                # Retry on 429, 500, 502, 503, 504, 528
                if e.response.status_code in [429, 500, 502, 503, 504, 528] and attempt < len(backoff_times):
                    logger.warning(f"[OpenRouter] {e.response.status_code} Error. Retrying in {wait_time}s... (Attempt {attempt+1})")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"[OpenRouter] Terminal Error {e.response.status_code}: {e.response.text}")
                raise e
            except Exception as e:
                if attempt < len(backoff_times):
                    logger.warning(f"Connection Error. Retrying in {wait_time}s... (Attempt {attempt+1})")
                    await asyncio.sleep(wait_time)
                    continue
                raise e

# ---------------------------------------------------------------------------
# High-Level Specialized Functions
# ---------------------------------------------------------------------------

async def detect_language_and_urgency_and_intent(email_text: str) -> Dict[str, Any]:
    """Uses FAST_MODEL for triage."""
    system_prompt = (
        "You are a customer support triage AI.\n"
        "Analyze the email and return ONLY a raw JSON object:\n"
        '  "language": "en" or "ar"\n'
        '  "intent": one of [refund, exchange, store_credit, escalate, unknown]\n'
        '  "urgency": one of [low, medium, high]\n'
        '  "confidence": float 0.0-1.0\n'
        "No markdown."
    )
    
    response_text = await call_llm(email_text, system_prompt, FAST_MODEL)

    from utils import extract_json_from_llm_response
    try:
        return json.loads(extract_json_from_llm_response(response_text))
    except Exception as e:
        logger.error(f"Failed to parse classification: {e}")
        return {"language": "en", "intent": "unknown", "urgency": "low", "confidence": 0.0}

async def generate_response(
    email_text: str,
    intent: str,
    urgency: str,
    language: str,
    context: str,
    fallback_mode: bool = False
) -> Dict[str, str]:
    """Uses COMPLEX_MODEL for grounded response generation."""
    system_prompt = (
        f"You are a Mumzworld support agent. Write in '{language}'.\n"
        f"Intent: {intent} | Urgency: {urgency}\n"
        "RULES:\n"
        "1. Return ONLY JSON: {'reasoning': '...', 'suggested_reply': '...'}.\n"
        "2. Use ONLY provided Context. Do NOT invent policies.\n"
        "3. If fallback_mode is True, ask for clarification politely.\n\n"
        f"Context:\n{context}"
    )
    
    prompt = f"Customer Email:\n{email_text}\n\nfallback_mode: {fallback_mode}"
    response_text = await call_llm(prompt, system_prompt, COMPLEX_MODEL)

    from utils import extract_json_from_llm_response
    try:
        return json.loads(extract_json_from_llm_response(response_text))
    except Exception as e:
        logger.error(f"Failed to parse generation: {e}")
        return {
            "reasoning": "Error parsing LLM output.",
            "suggested_reply": "We apologize for the delay. Our team is looking into your request."
        }
