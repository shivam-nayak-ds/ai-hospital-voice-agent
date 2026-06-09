import pytest
from src.agents.memory import SessionMemoryManager
from src.utils.message_helper import convert_messages_to_dicts

class MockMessage:
    def __init__(self, role, content, msg_type):
        self.role = role
        self.content = content
        self.type = msg_type

def test_prune_messages():
    # max_history_turns = 2 means keeping 4 chat messages (2 user + 2 assistant)
    memory_mgr = SessionMemoryManager(max_history_turns=2)
    
    system_msg = MockMessage("system", "You are a helpful assistant.", "system")
    chat_msgs = [
        MockMessage("user", "Hello 1", "human"),
        MockMessage("assistant", "Hi 1", "ai"),
        MockMessage("user", "Hello 2", "human"),
        MockMessage("assistant", "Hi 2", "ai"),
        MockMessage("user", "Hello 3", "human"),
        MockMessage("assistant", "Hi 3", "ai"),
    ]
    
    messages = [system_msg] + chat_msgs
    pruned = memory_mgr.prune_messages(messages)
    
    # Pruned list should contain the system message + the last 4 chat messages
    assert len(pruned) == 5
    assert pruned[0].type == "system"
    assert pruned[1].content == "Hello 2"
    assert pruned[2].content == "Hi 2"
    assert pruned[3].content == "Hello 3"
    assert pruned[4].content == "Hi 3"
