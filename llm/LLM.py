import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, TypedDict, Optional, Callable, Dict, Any
from anthropic import Anthropic
import os
import json
from util import get_environment_variable

class LLMMessage(TypedDict):
    role: str
    content: str

class ChatCompletion(TypedDict):
    model: str
    conversation: List[LLMMessage]


class LLM:
    def __init__(self, logging):
        self.api_key = get_environment_variable('ANT_API_KEY')
        self.model = get_environment_variable('CLAUDE_DEFAULT_MODEL')
        self.client = Anthropic(api_key=self.api_key)
        self.executor = ThreadPoolExecutor()
        self.completion_log: List[ChatCompletion] = []
        self.listeners = set()
        self.logging = logging

    async def create_chat_completion(self, system_message: str, user_message: str) -> List[Dict[str, Any]]:
        conversation = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        return await self.create_conversation_completion(conversation)

    async def create_conversation_completion(self, conversation: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        messages = [
            {"role": "assistant" if msg["role"] == "system" else msg["role"], "content": msg["content"]}
            for msg in conversation
        ]

        if messages[0]["role"] != "user":
            messages.insert(0, {"role": "user", "content": "Hello!"})

        response = self.client.messages.create(
            model=self.model,
            messages=messages,
            max_tokens=4000,
            tools=[
                {
                    "name": "create_action",
                    "description": "Create a structured action for the AI system to execute",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "actions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "action": {
                                            "type": "string",
                                            "enum": ["send_message_to_student", "query_file_system", "send_message_to_stratos", "send_message_to_spaceship"],
                                            "description": "The type of action to perform"
                                        },
                                        "params": {
                                            "type": "object",
                                            "properties": {
                                                "message": {"type": "string"},
                                                "contents": {"type": "string"},
                                                "command": {"type": "string"},
                                                "should_reassess": {"type": "boolean"},
                                                "reason": {"type": "string"}
                                            }
                                        }
                                    },
                                    "required": ["action", "params"]
                                }
                            }
                        },
                        "required": ["actions"]
                    }
                }
            ]
        )

        actions = []
        try:
            for content_item in response.content:
                if hasattr(content_item, 'name') and content_item.name == "create_action":
                    if hasattr(content_item, 'input') and isinstance(content_item.input, dict):
                        actions.extend(content_item.input.get("actions", []))
        except Exception as e:
            logging.error(f"Error processing response content: {e}")
            logging.debug(f"Response content: {response.content}")

        if not actions:
            logging.warning("No actions were generated from the LLM response.")

        return actions
    
    def add_completion_listener(self, listener: Callable[[ChatCompletion], None]) -> None:
        self.listeners.add(listener)

    def remove_completion_listener(self, listener: Callable[[ChatCompletion], None]) -> None:
        self.listeners.discard(listener)