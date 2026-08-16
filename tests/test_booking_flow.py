import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.agents.ananya_agent import AshaSwarm
from src.utils.logger import custom_logger as logger


async def run_test():
    logger.info("Starting programmatic booking flow verification...")
    agent = AshaSwarm(user_id="programmatic_test_user")
    
    # Multi-turn conversational inputs to simulate the symptom and confirmation fix
    turns = [
        "Book appointment",
        "7089091461",
        "1234",
        "Amit",
        "tomorrow",
        "10:00 AM"
    ]
    
    for turn_idx, user_input in enumerate(turns, start=1):
        print(f"\n[Turn {turn_idx}] User: {user_input}")
        print("Asha: ", end="", flush=True)
        
        response_tokens = []
        async for token in agent.run(user_input):
            print(token, end="", flush=True)
            response_tokens.append(token)
        print()
        
    logger.success("Programmatic booking flow verification complete!")

if __name__ == "__main__":
    asyncio.run(run_test())
