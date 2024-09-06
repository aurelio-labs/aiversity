import json
import asyncio
from starlette.websockets import WebSocket

class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self.message_queues = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        if user_id in self.message_queues:
            await self.send_queued_messages(user_id)

    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_message(self, user_id: str, message):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
                print(f"Sent WebSocket message to user {user_id}: {json.dumps(message)[:100]}...")
            except Exception as e:
                print(f"Error sending WebSocket message to user {user_id}: {str(e)}")
                self.queue_message(user_id, message)
        else:
            print(f"No active WebSocket connection for user {user_id}")
            self.queue_message(user_id, message)

    def queue_message(self, user_id: str, message):
        if user_id not in self.message_queues:
            self.message_queues[user_id] = []
        self.message_queues[user_id].append(message)

    async def send_queued_messages(self, user_id: str):
        if user_id in self.message_queues:
            while self.message_queues[user_id]:
                message = self.message_queues[user_id].pop(0)
                await self.send_message(user_id, message)

    async def broadcast(self, message):
        for websocket in self.active_connections.values():
            await websocket.send_text(json.dumps(message))

    async def send_actions(self, user_id: str, actions):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(
                json.dumps({"type": "actions", "data": actions})
            )

    async def send_execution_update(self, user_id: str, update_message: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(
                json.dumps({"type": "execution_update", "data": update_message})
            )
