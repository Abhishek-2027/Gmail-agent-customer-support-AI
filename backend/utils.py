import re

def preprocess_email(text: str) -> str:
    """
    Cleans up noisy email text:
    - Removes common signatures and greetings
    - Normalizes whitespace
    """
    if not text or not text.strip():
        return ""
    
    # Simple regex to remove common English and Arabic signatures
    # (Very basic version for prototype)
    signatures = [
        r"(?i)best regards,.*",
        r"(?i)kind regards,.*",
        r"(?i)sincerely,.*",
        r"(?i)thanks,.*",
        r"مع تحياتي.*",
        r"شكرا.*"
    ]
    
    cleaned = text
    for sig in signatures:
        cleaned = re.sub(sig, "", cleaned, flags=re.DOTALL)
    
    # Remove leading/trailing whitespaces and extra newlines
    cleaned = re.sub(r'\n+', '\n', cleaned).strip()
    return cleaned

def extract_json_from_llm_response(text: str) -> str:
    """
    Extracts JSON from an LLM response that might have markdown formatting or extra text.
    """
    # 1. Try to find markdown code blocks
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # 2. Try to find the first '{' and last '}'
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end+1].strip()
    
    # 3. Fallback to just stripping
    return text.strip()
