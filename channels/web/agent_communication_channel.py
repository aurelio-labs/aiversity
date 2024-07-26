from typing import List
from channels.communication_channel import CommunicationChannel
from ARCANE.types import ChatMessage, create_chat_message

class AgentCommunicationChannel(CommunicationChannel):
    def __init__(self, sender: str, message: str, arcane_system):
        self.sender = sender
        self.message = message
        self.arcane_system = arcane_system
        self.messages: List[ChatMessage] = [create_chat_message(sender, message)]

    async def send_message(self, text: str):
        # In agent-to-agent communication, we don't send messages back directly.
        # Instead, we log the message and potentially trigger a new NIACL message.
        chat_message = create_chat_message(self.arcane_system.name, text)
        self.messages.append(chat_message)
        print(f"Agent {self.arcane_system.name} generated response: {text[:50]}...")
        
        # Here, we could trigger a new NIACL message if needed
        # await self.arcane_system.send_niacl_message(self.sender, text)

    async def get_message_history(self, message_count: int) -> List[ChatMessage]:
        return self.messages[-message_count:]

    async def get_last_message(self) -> str:
        return self.message

    def describe(self) -> str:
        return f"Agent Communication (Sender: {self.sender})"

    async def send_actions(self, actions: List[dict]):
        # For agent communication, we might not need to send actions back
        # But we can log them for debugging or future use
        print(f"Agent {self.arcane_system.name} executed actions: {actions}")

    async def send_execution_update(self, update_message: str):
        # Similar to send_actions, we might just log this
        print(f"Execution update for {self.arcane_system.name}: {update_message}")