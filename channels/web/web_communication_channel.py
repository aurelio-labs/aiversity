from ARCANE.types import ChatMessage, create_chat_message
from channels.communication_channel import CommunicationChannel
from channels.web.web_socket_connection_manager import WebSocketConnectionManager


class WebCommunicationChannel(CommunicationChannel):

    def __init__(self, messages: [ChatMessage],
                 web_socket: WebSocketConnectionManager, arcane_system):
        self.arcane_system = arcane_system
        self.messages: [ChatMessage] = messages
        self.web_socket = web_socket

    async def send_message(self, text):
        print("WebCommunicationChannel.send_message: " + text)
        chat_message = create_chat_message(self.arcane_system.name, text)
        await self.web_socket.send_message(chat_message)
        print("WebCommunicationChannel sent message!")

    async def get_message_history(self, message_count) -> [ChatMessage]:
        return self.messages

    def describe(self):
        return "Web"
