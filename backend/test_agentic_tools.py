import asyncio
from pipeline import run_pipeline

async def test_order_lookup():
    print("--- Testing Agentic Tool Use (Order Lookups) ---")
    
    test_cases = [
        {
            "name": "Valid Order (Delivered)",
            "text": "Hi, where is my order MW-1001? I haven't seen it yet."
        },
        {
            "name": "Valid Order (In Transit)",
            "text": "Can you check the status of MW-2002? I need it soon."
        },
        {
            "name": "Missing Order ID",
            "text": "Where is my package? I've been waiting for days!"
        },
        {
            "name": "Non-existent Order ID",
            "text": "Status of MW-9999 please."
        }
    ]
    
    for case in test_cases:
        print(f"\nTest Case: {case['name']}")
        print(f"Email: {case['text']}")
        result = await run_pipeline(case['text'])
        print(f"Detected Intent: {result['intent']}")
        print(f"AI Reasoning: {result['reasoning']}")
        print(f"Suggested Reply: {result['suggested_reply'][:150]}...")

if __name__ == "__main__":
    asyncio.run(test_order_lookup())
