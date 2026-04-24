import json
from typing import List, Dict
from src.llm.providers.factory import LLMFactory
from src.agent.prompts import ASHA_SYSTEM_PROMPT
from src.agent.schemas import ASHA_TOOL_SCHEMAS
from src.agent.tools import TOOL_MAP
from src.utils.logger import custom_logger as logger

class AshaAgent:
    def __init__(self):
        # 1. Brain & Tools
        self.llm = LLMFactory.get_provider("groq")
        self.tools_schema = ASHA_TOOL_SCHEMAS
        
        # 2. Permanent Memory (Initial State)
        self.memory = [
            {"role": "system", "content": ASHA_SYSTEM_PROMPT}
        ]
        logger.success("Asha Agent: High-Intelligence Brain Active.")

    def run(self, user_input: str):
        """
        Main Agent Loop: Reasoning -> Acting -> Observing -> Speaking
        """
        self.memory.append({"role": "user", "content": user_input})
        
        # Limit to 5 iterations to prevent infinite loops (Senior Practice)
        for i in range(5):
            logger.info(f"Asha Thinking (Iteration {i+1})...")
            
            # 1. Call LLM with Tool Knowledge
            response_obj = self.llm.client.chat.completions.create(
                model=self.llm.model_name,
                messages=self.memory,
                tools=self.tools_schema,
                tool_choice="auto"
            )
            
            message = response_obj.choices[0].message
            self.memory.append(message) # Store LLM's thought/response

            # 2. Check if LLM wants to use a Tool
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Asha deciding to use Tool: {function_name}")
                    
                    # Execute the Tool
                    if function_name in TOOL_MAP:
                        tool_result = TOOL_MAP[function_name](**arguments)
                        logger.success(f"Tool Result: {tool_result}")
                        
                        # Add tool result to memory so LLM can see it
                        self.memory.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": str(tool_result)
                        })
                    else:
                        logger.error(f"Tool {function_name} not found!")
                
                # Continue the loop so LLM can process the tool result
                continue
            
            # 3. If no tool calls, this is the final answer
            logger.success("Asha has found the answer.")
            return message.content

if __name__ == "__main__":
    import time
    # E2E System Test
    agent = AshaAgent()
    
    print("\n--- ASHA AGENT LIVE TEST ---")
    q1 = "Hi, I am Rahul. What is the ICU visiting policy?"
    print(f"\nUser: {q1}\nAsha: {agent.run(q1)}")
    
    time.sleep(3) # Wait for rate limit reset
    
    q2 = "Is there any ICU bed available for me?"
    print(f"\nUser: {q2}\nAsha: {agent.run(q2)}")
    
    time.sleep(3) # Wait for rate limit reset
    
    q3 = "Okay, book an appointment with Dr. Ramesh for tomorrow at 10 AM."
    print(f"\nUser: {q3}\nAsha: {agent.run(q3)}")
