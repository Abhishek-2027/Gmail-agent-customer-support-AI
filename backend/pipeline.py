from typing import Dict, Any
from utils import preprocess_email, extract_order_id
from llm_engine import detect_language_and_urgency_and_intent, generate_response
from retrieval import retrieve_policy, get_context_string
from tools import get_order_details

def compute_confidence(classification_conf: float, rag_score: float, is_unknown: bool) -> float:
    """
    Computes a weighted confidence score.
    """
    if is_unknown:
        # Heavily penalize unknown intents to force fallback
        return min(classification_conf, 0.4)
    
    # Weighted average: 70% classification confidence, 30% RAG score (maxed at 1.0)
    # If no RAG context is found (rag_score=0), we rely mostly on classification conf.
    normalized_rag = min(rag_score * 2.0, 1.0) # boost rag score as cosine sim can be low
    final_conf = (classification_conf * 0.7) + (normalized_rag * 0.3)
    
    return round(min(max(final_conf, 0.0), 1.0), 2)

async def run_pipeline(email_text: str) -> Dict[str, Any]:
    """
    Executes the entire end-to-end pipeline.
    """
    # Step 1: Preprocessing
    clean_text = preprocess_email(email_text)
    if not clean_text:
         return {
            "intent": "unknown",
            "urgency": "low",
            "confidence": 0.0,
            "reasoning": "Email is empty or only contains noise.",
            "suggested_reply": "Could you please provide more details about your request? Your email appears to be empty."
        }

    # Step 2 & 3 & 4: Language, Intent, Urgency (Fast LLM)
    fast_classification = await detect_language_and_urgency_and_intent(clean_text)
    
    intent = fast_classification.get("intent", "unknown")
    urgency = fast_classification.get("urgency", "low")
    language = fast_classification.get("language", "en")
    class_conf = float(fast_classification.get("confidence", 0.0))

    # Determine if fallback is needed
    is_unknown = (intent == "unknown" or class_conf < 0.5)

    # Step 5: Retrieval (RAG) & Tool Calling
    # PROACTIVE TOOL CALLING: If we see an Order ID, we always check it!
    order_id = extract_order_id(clean_text)
    tool_output = ""
    if order_id:
        tool_output = get_order_details(order_id)
    elif intent == "order_tracking":
        tool_output = "No Order ID found in the email. Ask the customer for their MW-XXXX order number."

    # Standard RAG query
    rag_query = f"{intent} {clean_text}"
    retrieved_docs = retrieve_policy(rag_query)
    context_str = get_context_string(retrieved_docs)
    
    # Combine context with tool output if available
    if tool_output:
        context_str = f"TOOL_OUTPUT (Order Data): {tool_output}\n\n" + context_str
    
    rag_score = max([d["score"] for d in retrieved_docs]) if retrieved_docs else 0.0

    # Step 6: Compute Final Confidence
    final_confidence = compute_confidence(class_conf, rag_score, is_unknown)

    # CRITICAL FIX: If a tool successfully found data, we are much more confident!
    if tool_output and "Order Found" in tool_output:
        final_confidence = max(final_confidence, 0.85)
        is_unknown = False
        intent = "order_tracking"

    # Re-evaluate fallback mode based on final confidence
    is_unknown = (is_unknown or final_confidence < 0.5)
    if is_unknown and not tool_output:
        intent = "unknown"

    # Step 7: Generate Final Response (Complex LLM)
    response_generation = await generate_response(
        email_text=clean_text,
        intent=intent,
        urgency=urgency,
        language=language,
        context=context_str,
        fallback_mode=is_unknown
    )

    reasoning = response_generation.get("reasoning", "No reasoning provided.")
    suggested_reply = response_generation.get("suggested_reply", "Could you please clarify your request?")

    # Return structured output
    return {
        "intent": intent,
        "urgency": urgency,
        "confidence": final_confidence,
        "reasoning": reasoning,
        "suggested_reply": suggested_reply
    }
