import json

from starlette.websockets import WebSocket


class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_message(self, user_id: str, message):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
                print(
                    f"Sent WebSocket message to user {user_id}: {json.dumps(message)[:100]}..."
                )  # Log sent messages
            except Exception as e:
                print(f"Error sending WebSocket message to user {user_id}: {str(e)}")
        else:
            print(f"No active WebSocket connection for user {user_id}")

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
