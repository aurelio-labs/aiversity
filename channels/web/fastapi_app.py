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


class FastApiApp:
    def __init__(self, arcane_system: ArcaneSystem, llm: LLM, port: int):
        self.app = FastAPI()
        self.arcane_system = arcane_system
        self.chatConnectionManager = WebSocketConnectionManager()
        self.llmConnectionManager = WebSocketConnectionManager()

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

    # noinspection PyUnusedLocal
    async def custom_exception_handler(self, request: Request, exc: Exception):
        """
        Custom exception handler that logs the stack trace and returns a JSON response.
        """
        print("custom_exception_handler called")
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return JSONResponse(content={"error": str(exc), "traceback": traceback_str}, status_code=500)

    async def llm_completion_listener(self, completion: ChatCompletion):
        await self.llmConnectionManager.send_message(completion)

    async def send_message_to_frontend(self, message: str):
        await self.chatConnectionManager.send_message(message)

    def setup_routes(self):
        app = self.app

        @app.websocket("/ws-chat/")
        async def websocket_endpoint_chat(websocket: WebSocket):
            print("websocket_endpoint_chat called")
            await self.chatConnectionManager.connect(websocket)

        @app.websocket("/ws-llmlog/")
        async def websocket_endpoint_llmlog(websocket: WebSocket):
            print("websocket_endpoint_llmlog called")
            await self.llmConnectionManager.connect(websocket)

        # noinspection PyUnusedLocal
        @app.exception_handler(Exception)
        async def custom_exception_handler(request: Request, exc: Exception):
            """
            Custom exception handler that logs the stack trace and returns a JSON response.
            """
            traceback_str = traceback.format_exc()
            print(traceback_str)
            return JSONResponse(content={"error": str(exc), "traceback": traceback_str}, status_code=500)

        @app.post("/chat/")
        async def chat(request: Request):
            data = await request.json()
            message = data.get('message', '')
            messages: [ChatMessage] = [create_chat_message("api-user", message)]
            communication_channel = WebCommunicationChannel(messages, self.chatConnectionManager, self.arcane_system)

            try:
                await self.arcane_system.process_incoming_user_message(communication_channel)
                print("here")
                
                # Send a test async message back to the frontend
                # await self.send_message_to_frontend("This is a test async message from the backend.")
                
                return JSONResponse(content={"success": True}, status_code=200)
            except Exception as e:
                print("Damn, something went wrong while processing incoming user message!")
                traceback_str = traceback.format_exc()
                print(traceback_str)
                await self.send_message_to_frontend(f"Damn! Something went wrong: {str(e)}")
                return JSONResponse(content={"success": False}, status_code=500)
            



        @app.get("/chat/")
        async def chat_get(message: str):
            """
            For testing purposes. Lets you send a single chat message and see the response (if any)
            """
            if not message:
                raise HTTPException(status_code=400, detail="message parameter is required")
            messages = [create_chat_message("api-user", message)]
            communication_channel = WebCommunicationChannel(messages, self.chatConnectionManager)

            try:
                await self.arcane_system.process_incoming_user_message(communication_channel)
                return f"Message sent to {self.arcane_system.name}"
            except Exception as e:
                traceback_str = traceback.format_exc()
                print(traceback_str)
                return JSONResponse(content={"error": str(e), "traceback": traceback_str}, status_code=400)

        @app.get("/llmlog/")
        async def get_llm_completions():
            return self.llm.get_completion_log()

        @app.get("/", response_class=HTMLResponse)
        def root():
            return (f'<html>{self.arcane_system.name} SYSTEM RESPONSE: The backend is up and running! '
                    '<a href="chat?message=hi">/chat?message=hi</a></html>')

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