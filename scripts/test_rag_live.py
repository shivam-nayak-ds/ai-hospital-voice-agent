import asyncio
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools.rag_tool import retrieve_hospital_info

async def main():
    queries = [
        "Who is the cardiologist and what is the fee?",
        "What are the visiting hours for ICU?",
        "What is the price of Knee Replacement surgery?",
    ]

    print("\n" + "="*60)
    print("🏥 TESTING RAG RETRIEVAL PIPELINE LIVE")
    print("="*60)

    for q in queries:
        print(f"\n❓ Query: {q}")
        result = await retrieve_hospital_info(q, limit=2)
        print("📄 Answer / Context:")
        print(result)
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
