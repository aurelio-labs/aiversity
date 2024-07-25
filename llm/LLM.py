import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, TypedDict, Optional, Callable, Dict, Any
from anthropic import Anthropic
import os
import json
from util import get_environment_variable
import logging

class LLMMessage(TypedDict):
    role: str
    content: str

class ChatCompletion(TypedDict):
    model: str
    conversation: List[LLMMessage]

class LLM:
    def __init__(self, logging, api_key, model):
        self.api_key = api_key
        self.model = model
        self.client = Anthropic(api_key=self.api_key)
        self.executor = ThreadPoolExecutor()
        self.completion_log: List[ChatCompletion] = []
        self.listeners = set()
        self.logging = logging

    async def create_chat_completion(self, system_message: str, user_message: str, tool_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        conversation = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        return await self.create_conversation_completion(conversation, tool_config)

    async def create_conversation_completion(self, conversation: List[Dict[str, str]], tool_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        messages = [
            {"role": "assistant" if msg["role"] == "system" else msg["role"], "content": msg["content"]}
            for msg in conversation
        ]

        if messages[0]["role"] != "user":
            messages.insert(0, {"role": "user", "content": "Hello!"})

        tool = self.get_dynamic_tool(tool_config)

        response = self.client.messages.create(
            model=self.model,
            messages=messages,
            max_tokens=4000,
            tools=[tool]
        )

        actions = []
        try:
            for content_item in response.content:
                if hasattr(content_item, 'name') and content_item.name == tool_config['name']:
                    if hasattr(content_item, 'input') and isinstance(content_item.input, dict):
                        actions.append(content_item.input)
        except Exception as e:
            self.logging.error(f"Error processing response content: {e}")
            self.logging.debug(f"Response content: {response.content}")

        if not actions:
            self.logging.warning(f"No {tool_config['name']} were generated from the LLM response.")

        return actions

    def get_dynamic_tool(self, config: Dict[str, Any]):
        return {
            "name": config['name'],
            "description": config['description'],
            "input_schema": {
                "type": "object",
                "properties": {
                    config['output_key']: config['output_schema']
                },
                "required": [config['output_key']]
            }
        }

    def add_completion_listener(self, listener: Callable[[ChatCompletion], None]) -> None:
        self.listeners.add(listener)

    def remove_completion_listener(self, listener: Callable[[ChatCompletion], None]) -> None:
        self.listeners.discard(listener)

    # Utility method to get predefined tool configurations
    @staticmethod
    def get_tool_config(tool_type: str) -> Dict[str, Any]:
        tool_configs = {
            "set_goal": {
                "name": "set_goal",
                "description": "Set a goal for the AI system. Remember that any goal involving retrieving or processing information must include communicating that information to the user.",
                "output_key": "goal",
                "output_schema": {
                    "type": "string",
                    "description": "The goal to be set"
                }
            },
            "create_action": {
                "name": "create_action",
                "description": "Create a structured action for the AI system to execute. IMPORTANT: After any action that retrieves information or performs a task, you MUST include a send_message_to_student action to communicate the results or acknowledge the completion of the task to the user.",
                "output_key": "actions",
                "output_schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["send_message_to_student", "query_file_system", "send_message_to_stratos", "send_message_to_spaceship", "view_file_contents", "edit_file_contents", "create_new_file", "run_python_file"],
                                "description": "The type of action to perform"
                            },
                            "params": {
                                "type": "object",
                                "properties": {
                                    "message": {"type": "string"},
                                    "contents": {"type": "string"},
                                    "command": {"type": "string"},
                                    "file_path": {"type": "string"},
                                    "content": {"type": "string"}
                                }
                            }
                        },
                        "required": ["action", "params"]
                    }
                }
            },
            "goal_check": {
                "name": "goal_check",
                "description": "Check if the current goal has been achieved. IMPORTANT: A goal is not considered fully achieved until the results or completion of tasks have been communicated to the user via a send_message_to_student action.",
                "output_key": "goal_achieved",
                "output_schema": {
                    "type": "boolean",
                    "description": "Whether the goal has been achieved"
                }
            },
            "reassessment_decision": {
                "name": "reassessment_decision",
                "description": "Decide whether to reassess the current goal. Consider whether all retrieved information or completed tasks have been communicated to the user.",
                "output_key": "reassessment_decision",
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "should_reassess": {
                            "type": "boolean",
                            "description": "Whether the goal should be reassessed"
                        },
                        "reason": {
                            "type": "string",
                            "description": "The reason for the decision"
                        }
                    },
                    "required": ["should_reassess", "reason"]
                }
            }
        }
        return tool_configs.get(tool_type, {})