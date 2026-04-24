import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.llm.providers.brain import LLMBrain
from src.utils.logger import custom_logger as logger

def main():
    logger.info("Asha AI Hospital Agent Session Started.")
    brain = LLMBrain()
    
    print("\n" + "="*50)
    print("🏥 Asha AI Hospital Assistant (Terminal Mode)")
    print("Type 'exit' to quit. Let's talk!")
    print("="*50 + "\n")

    while True:
        try:
            user_input = input("👤 You: ")
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("\nAsha: Goodbye! Have a healthy day ahead.")
                break
            
            print("🤖 Asha: ", end="", flush=True)
            
            # Streaming the response token by token
            for token in brain.stream_asha_response(user_input):
                print(token, end="", flush=True)
            
            print("\n") # Line break after response

        except KeyboardInterrupt:
            print("\nSession ended.")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            print(f"\n[Asha is having some trouble, please try again later.]")

if __name__ == "__main__":
    main()
