import json
import re
from typing import List, Dict, Generator
from src.llm.providers.factory import LLMFactory
from src.agent.prompts import ASHA_SYSTEM_PROMPT
from src.agent.schemas import ASHA_TOOL_SCHEMAS
from src.agent.tools import TOOL_MAP
from src.utils.logger import custom_logger as logger

from src.agent.specialists import APPOINTMENT_SPECIALIST_PROMPT, EMERGENCY_SPECIALIST_PROMPT, KNOWLEDGE_SPECIALIST_PROMPT

class AshaAgent:
    def __init__(self):
        self.llm = LLMFactory.get_provider("groq")
        self.memory = [{"role": "system", "content": ASHA_SYSTEM_PROMPT}]
        logger.success("Asha Multi-Agent Supervisor Active.")

    def _clean_text(self, text: str) -> str:
        """Nuclear filter to remove ANY technical artifacts or code-like speech."""
        text = re.sub(r'<[^>]+>', '', text)
        technical_patterns = [
            r'function\s*=\s*\w+', r'search_\w+', r'book_\w+', 
            r'request_\w+', r'\{.*?\}', r'\[.*?\]', r'mean of function', r'tool\w+'
        ]
        for pattern in technical_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.replace("=", "").replace("_", " ").strip()

    def _humanize_response(self, text: str) -> str:
        """Removes technical artifacts and ensures clean Hinglish output."""
        text = self._clean_text(text)
        if not text or len(text) < 2: 
            return "जी, मैं सुन रही हूँ। बोलिए?"
            
        return text.strip()

    def _get_filler(self, intent: str) -> str:
        """Returns a natural human filler based on intent."""
        import random
        
        if intent == "emergency":
            return "घबराइए मत..."
            
        general_fillers = [
            "जी...",
            "हाँ जी...",
            "बिल्कुल...",
            "एक सेकंड...",
            "ज़रूर...",
            "" # Sometimes no filler is more natural
        ]
        
        return random.choice(general_fillers)

    def run(self, user_input: str, intent: str = "general") -> Generator[str, None, None]:
        # 1. Update Specialist Context based on Intent (Step 2: Multi-Agent)
        if intent == "appointment":
            self.memory[0]["content"] = ASHA_SYSTEM_PROMPT + "\n\n" + APPOINTMENT_SPECIALIST_PROMPT
        elif intent == "emergency":
            self.memory[0]["content"] = ASHA_SYSTEM_PROMPT + "\n\n" + EMERGENCY_SPECIALIST_PROMPT
        else:
            self.memory[0]["content"] = ASHA_SYSTEM_PROMPT

        self.memory.append({"role": "user", "content": user_input})
        
        # 🧠 Memory Pruning (Sliding Window) to prevent Groq Rate Limit
        if len(self.memory) > 12:
            new_memory = [self.memory[0]] # Always keep System Prompt
            # Find a safe index to slice (must start with a 'user' message)
            safe_idx = len(self.memory) - 8
            while safe_idx > 1:
                m = self.memory[safe_idx]
                role = m.get("role") if isinstance(m, dict) else m.role
                if role == "user":
                    break
                safe_idx -= 1
            new_memory.extend(self.memory[safe_idx:])
            self.memory = new_memory
            
        # 2. Start Execution
        for i in range(3): 
            kwargs = {
                "model": self.llm.model_name,
                "messages": self.memory,
                "temperature": 0.1
            }
            # Only allow tools on the first iteration to prevent infinite tool loops
            if i == 0:
                kwargs["tools"] = ASHA_TOOL_SCHEMAS
                kwargs["tool_choice"] = "auto"
                
            response = self.llm.client.chat.completions.create(**kwargs)
            
            message = response.choices[0].message

            if message.tool_calls:
                self.memory.append(message)
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Asha Specialist Executing: {function_name}")
                    
                    if function_name in TOOL_MAP:
                        tool_result = TOOL_MAP[function_name](**arguments)
                        self.memory.append({"role": "tool", "tool_call_id": tool_call.id, "name": function_name, "content": str(tool_result)})
                    else:
                        self.memory.append({"role": "tool", "tool_call_id": tool_call.id, "name": function_name, "content": "Error: Tool not found."})
                continue
            
            if message.content:
                final_text = self._humanize_response(message.content)
                self.memory.append({"role": "assistant", "content": final_text})
                
                # Streaming with slight delay for rhythm
                for word in final_text.split():
                    yield word + " "
                return
        
        yield "Ji, main koshish kar rahi hoon. Ek minute rukiye."
