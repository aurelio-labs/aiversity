from datetime import datetime, timezone
from typing import TypedDict, Dict


# Make sure this stays in sync with the client-side version (types.ts)


class ChatMessage(TypedDict):
    sender: str
    content: str
    time_utc: str  # // formatted like 2023-01-30T13:45:00Z


def create_chat_message(sender: str, content: str) -> ChatMessage:
    now_utc = datetime.now(timezone.utc)
    formatted_time = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    return {"sender": sender, "content": content, "time_utc": formatted_time}


def stringify_chat_message(chat_message: ChatMessage):
    return f"<{chat_message['time_utc']}> [{chat_message['sender']}] {chat_message['content']}"


def stringify_chat_history(conversation: [ChatMessage]):
    return "\n".join(f"- {stringify_chat_message(message)}" for message in conversation)


# If you change this, also update the code in memory/weaviate_memory_manager.py
class Memory(TypedDict):
    time_utc: str
    content: str


def create_memory(content: str) -> Memory:
    return {
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "content": content
    }


LayerState = Dict[str, str]
