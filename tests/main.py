import sys
import asyncio
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.agents.ananya_agent import AshaSwarm
from src.utils.logger import custom_logger as logger

async def main():
    logger.info("Asha AI Hospital Agent Session Started.")
    agent = AshaSwarm(user_id="local_test_user")

    print("\n" + "=" * 50)
    print(" Asha AI Hospital Assistant")
    print("Type 'exit' to quit.")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input(" You: ")

            if user_input.lower() in ["exit", "quit", "bye"]:
                print("\nAsha: Goodbye. Have a healthy day ahead.")
                break

            if not user_input.strip():
                continue

            print(" Asha: ", end="", flush=True)
            async for token in agent.run(user_input):
                print(token, end="", flush=True)

            print("\n")

        except KeyboardInterrupt:
            print("\nSession ended.")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            print("\n[Asha is having some trouble. Please try again later.]")


if __name__ == "__main__":
    asyncio.run(main())
