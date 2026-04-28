import httpx
import asyncio
import json

async def test():
    email = "مرحبا، لقد استلمت طلبيتي بالأمس ولكن حليب الأطفال كان تنبعث منه رائحة غريبة وطفلي تقيأ. هذا خطير جدا!"
    # Translation: Hello, I received my order yesterday but the baby formula smelled weird and my baby threw up. This is very dangerous!
    
    payload = {"email_text": email}
    
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/analyze", json=payload, timeout=60.0)
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(test())
