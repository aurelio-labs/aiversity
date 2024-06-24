import traceback
import uvicorn
from fastapi import FastAPI, Request, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import HTMLResponse
from ARCANE.arcane_system import ArcaneSystem
from ARCANE.types import ChatMessage, create_chat_message
from channels.web.web_communication_channel import WebCommunicationChannel
from channels.web.web_socket_connection_manager import WebSocketConnectionManager
from llm.LLM import LLM, ChatCompletion
import signal
import asyncio
import uuid
import json

class FastApiApp:
    def __init__(self, arcane_system: ArcaneSystem, llm: LLM, port: int):
        self.app = FastAPI()
        self.arcane_system = arcane_system
        self.chatConnectionManager = WebSocketConnectionManager()
        self.llmConnectionManager = WebSocketConnectionManager()
        self.user_connections = {}  # Store WebSocket connections by user_id

        self.app.add_exception_handler(Exception, self.custom_exception_handler)

        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.setup_routes()

        self.llm = llm
        self.port = port
        self.server = None

    async def custom_exception_handler(self, request: Request, exc: Exception):
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return JSONResponse(content={"error": str(exc), "traceback": traceback_str}, status_code=500)

    async def llm_completion_listener(self, completion: ChatCompletion):
        # Broadcast the completion to all connected clients
        for user_id, websocket in self.llmConnectionManager.active_connections.items():
            await websocket.send_text(json.dumps(completion))

    async def send_message_to_frontend(self, user_id: str, message: str):
        if user_id in self.user_connections:
            await self.user_connections[user_id].send_text(json.dumps(message))

    def setup_routes(self):
        app = self.app

        @app.websocket("/ws-chat/{user_id}")
        async def websocket_endpoint_chat(websocket: WebSocket, user_id: str):
            await self.chatConnectionManager.connect(user_id, websocket)
            try:
                while True:
                    data = await websocket.receive_text()
                    await self.process_websocket_message(user_id, data)
            except Exception as e:
                print(f"WebSocket error for user {user_id}: {str(e)}")
            finally:
                await self.chatConnectionManager.disconnect(user_id)

        @app.websocket("/ws-llmlog/")
        async def websocket_endpoint_llmlog(websocket: WebSocket):
            await self.llmConnectionManager.connect(websocket)

        @app.post("/chat/")
        async def chat(request: Request):
            data = await request.json()
            message = data.get('message', '')
            user_id = data.get('user_id', str(uuid.uuid4()))  # Generate a new user_id if not provided
            messages: [ChatMessage] = [create_chat_message("api-user", message)]
            communication_channel = WebCommunicationChannel(messages, self.chatConnectionManager, self.arcane_system, user_id)

            try:
                await self.arcane_system.process_incoming_user_message(communication_channel, user_id)
                return JSONResponse(content={"success": True, "user_id": user_id}, status_code=200)
            except Exception as e:
                traceback_str = traceback.format_exc()
                print(traceback_str)
                await self.send_message_to_frontend(user_id, f"An error occurred: {str(e)}")
                return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

        @app.get("/chat/")
        async def chat_get(message: str, user_id: str = None):
            if not message:
                raise HTTPException(status_code=400, detail="message parameter is required")
            if not user_id:
                user_id = str(uuid.uuid4())
            messages = [create_chat_message("api-user", message)]
            communication_channel = WebCommunicationChannel(messages, self.chatConnectionManager, self.arcane_system, user_id)

            try:
                await self.arcane_system.process_incoming_user_message(communication_channel, user_id)
                return f"Message sent to {self.arcane_system.name} for user {user_id}"
            except Exception as e:
                traceback_str = traceback.format_exc()
                print(traceback_str)
                return JSONResponse(content={"error": str(e), "traceback": traceback_str}, status_code=400)

        @app.get("/llmlog/")
        async def get_llm_completions():
            return self.llm.get_completion_log()

        @app.get("/", response_class=HTMLResponse)
        def root():
            return f'<html>{self.arcane_system.name} SYSTEM RESPONSE: The backend is up and running! <a href="chat?message=hi">/chat?message=hi</a></html>'


    async def process_websocket_message(self, user_id: str, message: str):
        messages: [ChatMessage] = [create_chat_message("api-user", message)]
        communication_channel = WebCommunicationChannel(messages, self.chatConnectionManager, self.arcane_system, user_id)
        response = await self.arcane_system.process_incoming_user_message(communication_channel, user_id)
        
        # Process the response
        processed_response = self.process_response(response)
        
        # Send the processed response
        await self.chatConnectionManager.send_message(user_id, create_chat_message(self.arcane_system.name, processed_response))

    def process_response(self, response):
        if isinstance(response, str):
            try:
                actions = json.loads(response)
                if isinstance(actions, list):
                    for action in actions:
                        if action.get('action') == 'send_message_to_student':
                            return action.get('message', '')
                return response  # Return original if not expected format
            except json.JSONDecodeError:
                return response  # Return original if not valid JSON
        return str(response)  # Convert to string if not already

    def setup_listeners(self):
        self.llm.add_completion_listener(self.llm_completion_listener)

    async def run(self):
        self.setup_listeners()
        config = uvicorn.Config(app=self.app, host="localhost", port=self.port, log_level="error")
        self.server = uvicorn.Server(config)

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.shutdown)

        print(f"Running server on port {self.port}...")
        await self.server.serve()
        print(f"Server on port {self.port} has shut down.")

    def shutdown(self):
        print(f"Shutting down server on port {self.port}...")
        if self.server:
            self.server.should_exit = True