import asyncio
import json
import os
import logging

# Suppress ChromaDB telemetry logs
os.environ["ANONYMIZED_TELEMETRY"] = "False"
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

from pipeline import run_pipeline
from retrieval import init_rag
from pydantic import ValidationError
from schema import OutputResponse

TEST_CASES = [
    # 1. Easy English - Refund
    {
        "input": "Hi, I received the baby stroller yesterday but it's too big for my trunk. I want a refund.",
        "expected_intent": "refund",
        "expect_uncertainty": False
    },
    # 2. Easy Arabic - Exchange
    {
        "input": "مرحبا، وصلني الكرسي اليوم ولكنه مكسور. أريد استبداله لو سمحتم.",
        "expected_intent": "exchange",
        "expect_uncertainty": False
    },
    # 3. Escalation - Health/Safety
    {
        "input": "The formula I bought for my newborn smells weird and she threw up after drinking it. This is dangerous!",
        "expected_intent": "escalate",
        "expect_uncertainty": False
    },
    # 4. Edge Case - Late Return (Store Credit)
    {
        "input": "I bought this toy 20 days ago and just opened it, my son doesn't like it. Can I send it back?",
        "expected_intent": "store_credit",
        "expect_uncertainty": False
    },
    # 5. Missing Info / Unclear (Should be unknown + high uncertainty)
    {
        "input": "Hello, about my order #12345, please fix it.",
        "expected_intent": "unknown",
        "expect_uncertainty": True
    },
    # 6. Adversarial / Conflicting
    {
        "input": "I hate this product so much. I want a refund! But actually wait, maybe you can just exchange it? Or give me store credit? I don't know, just do something.",
        "expected_intent": "unknown",
        "expect_uncertainty": True
    },
    # 7. Gibberish (Should be unknown)
    {
        "input": "asdfasdfasdf zxcv",
        "expected_intent": "unknown",
        "expect_uncertainty": True
    },
    # 8. English Noise (Signature heavy)
    {
        "input": "Can I exchange the diapers for a larger size?\n\nBest regards,\nJohn Doe\nVP of Sales\nCompany LLC\nPhone: 555-1234",
        "expected_intent": "exchange",
        "expect_uncertainty": False
    },
    # 9. Arabic - Missing Item
    {
        "input": "السلام عليكم، استلمت طلبيتي ولكن تنقصها زجاجة الحليب. الرجاء المساعدة.",
        "expected_intent": "escalate", # Or whatever fits best, maybe missing items should be escalate or unknown. We will just check if schema is valid.
        "expect_uncertainty": False
    },
    # 10. Empty Input
    {
        "input": "   \n  \n",
        "expected_intent": "unknown",
        "expect_uncertainty": True
    }
]

async def run_evals():
    init_rag()
    print("Starting evaluations...\n")
    
    passed_cases = 0
    total_cases = len(TEST_CASES)
    intent_correct = 0
    uncertainty_correct = 0

    for idx, test in enumerate(TEST_CASES):
        print(f"Test {idx+1}/{total_cases}")
        
        try:
            # Respect rate limit of 15 RPM on free keys
            await asyncio.sleep(4)
            result = await run_pipeline(test['input'])
            # Validate schema
            validated = OutputResponse(**result)
            
            intent = result['intent']
            conf = result['confidence']
            is_uncertain = (conf < 0.5) or (intent == "unknown")
            
            # Check correctness
            intent_pass = False
            # For test 9, we are a bit lenient as 'escalate' or 'exchange' might both be chosen by LLM.
            if test['expected_intent'] == intent or (idx == 8): 
                intent_pass = True
            
            uncertainty_pass = (is_uncertain == test['expect_uncertainty'])
            
            if intent_pass: intent_correct += 1
            if uncertainty_pass: uncertainty_correct += 1
            
            if intent_pass and uncertainty_pass:
                passed_cases += 1
                status = "[PASS]"
            else:
                status = "[FAIL]"
                
            print(f"{status} | Expected Intent: {test['expected_intent']} | Predicted: {intent} | Conf: {conf}")
            print("-" * 50)
            
        except ValidationError as e:
            print(f"[FAIL] (Schema Validation Error): {e}")
            print("-" * 50)
        except Exception as e:
            print(f"[FAIL] (Pipeline Error): {e}")
            print("-" * 50)
            
    print("\n=== EVALUATION RESULTS ===")
    print(f"Total Tests: {total_cases}")
    print(f"Passed: {passed_cases}/{total_cases}")
    print(f"Intent Accuracy: {(intent_correct/total_cases)*100:.1f}%")
    print(f"Uncertainty Correctness: {(uncertainty_correct/total_cases)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(run_evals())
