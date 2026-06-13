def get_message_content(msg) -> str:
    """
    Extracts the content string from a message (dict or LangChain BaseMessage).
    """
    if hasattr(msg, "content"):
        return msg.content
    elif isinstance(msg, dict):
        return msg.get("content", "")
    return str(msg)

def get_message_role(msg) -> str:
    """
    Extracts the role (user, assistant, system) from a message.
    """
    if hasattr(msg, "type"):
        t = msg.type
        if t == "human":
            return "user"
        elif t == "ai":
            return "assistant"
        return t
    elif isinstance(msg, dict):
        return msg.get("role", "")
    return "user"

def convert_messages_to_dicts(messages) -> list:
    """
    Converts a list of messages (dicts or LangChain BaseMessage objects) 
    into standard OpenAI-compatible dicts: [{"role": "user"|"assistant"|"system", "content": "..."}]
    """
    dicts = []
    for msg in messages:
        content = get_message_content(msg)
        role = get_message_role(msg)
        dicts.append({"role": role, "content": content})
    return dicts

