from ARCANE.types import ChatMessage, create_chat_message
from channels.communication_channel import CommunicationChannel
from channels.web.web_socket_connection_manager import WebSocketConnectionManager


class WebCommunicationChannel(CommunicationChannel):
    def __init__(self, messages: [ChatMessage],
                 web_socket: WebSocketConnectionManager, arcane_system, user_id: str):
        self.arcane_system = arcane_system
        self.messages: [ChatMessage] = messages
        self.web_socket = web_socket
        self.user_id = user_id

    async def send_message(self, text):
        print(f"WebCommunicationChannel.send_message for user {self.user_id}: {text}")
        chat_message = create_chat_message(self.arcane_system.name, text)
        await self.web_socket.send_message(self.user_id, chat_message)
        print("WebCommunicationChannel sent message!")

    async def get_message_history(self, message_count) -> [ChatMessage]:
        return self.messages[-message_count:]

    async def get_last_message(self) -> str:
        if self.messages:
            return self.messages[-1]['content']
        return ""
    
    async def send_actions(self, actions):
        print(f"WebCommunicationChannel.send_actions for user {self.user_id}: {actions}")
        await self.web_socket.send_actions(self.user_id, actions)
        print("WebCommunicationChannel sent actions!")

    def describe(self):
        return f"Web (User ID: {self.user_id})"
    
    async def send_execution_update(self, update_message: str):
        await self.web_socket.send_execution_update(self.user_id, update_message)