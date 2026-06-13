import sys
import asyncio
import pickle
from pathlib import Path

# Ensure project root is in PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.agents.ananya_agent import AshaSwarm
from src.utils.logger import custom_logger as logger

# Silence detailed logger outputs to keep the print console clean
logger.remove()

async def main():
    if len(sys.argv) < 2:
        print("Error: Missing input message.")
        sys.exit(1)
        
    user_message = sys.argv[1]
    
    # Session state path
    state_file = Path("scratch/test_session_state.pkl")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize swarm instance
    swarm = AshaSwarm(user_id="manual_test_session")
    
    # Load previous conversation state if it exists
    if state_file.exists():
        try:
            with open(state_file, "rb") as f:
                swarm.state = pickle.load(f)
        except Exception:
            pass
            
    # Execute turn
    response_text = ""
    async for chunk in swarm.run(user_message):
        response_text += chunk
        
    # Persist updated session state
    try:
        with open(state_file, "wb") as f:
            pickle.dump(swarm.state, f)
    except Exception:
        pass
        
    # Output raw reply text
    print(response_text)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
