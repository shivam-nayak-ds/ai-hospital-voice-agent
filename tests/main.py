import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.agent.orchestrator import AshaOrchestrator
from src.utils.logger import custom_logger as logger

def main():
    logger.info("Asha AI Hospital Agent Session Started (Orchestrated Mode).")
    # Using the Orchestrator instead of raw Agent
    orchestrator = AshaOrchestrator()
    
    print("\n" + "="*50)
    print(" Asha AI Hospital Assistant (Orchestrated Mode)")
    print("Type 'exit' to quit. Let's talk!")
    print("="*50 + "\n")

    while True:
        try:
            user_input = input(" You: ")
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("\nAsha: Goodbye! Have a healthy day ahead. 🙏")
                break
            
            if not user_input.strip():
                continue

            print(" Asha: ", end="", flush=True)
            
            # Orchestrator handles Guardrails -> Mapping -> Agent
            for token in orchestrator.handle_request(user_input):
                print(token, end="", flush=True)
            
            print("\n")

        except KeyboardInterrupt:
            print("\nSession ended.")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            print(f"\n[Asha is having some trouble, please try again later.]")

if __name__ == "__main__":
    main()
