import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, TypedDict, Optional, Callable, Dict, Any
from anthropic import Anthropic
import os
import json
from util import load_actions, get_environment_variable
import logging
import time
from datetime import datetime
import anthropic

from anthropic.types import TextBlock, ToolUseBlock

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
        self.log_folder = "llm_logs"
        os.makedirs(self.log_folder, exist_ok=True)

    def log_request_response(
        self, request: Dict[str, Any], response: Any, success: bool
    ):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        log_file = os.path.join(self.log_folder, f"{timestamp}_llm_log.json")
        log_data = {
            "timestamp": timestamp,
            "request": request,
            "response": response,
            "success": success,
        }
        with open(log_file, "w") as f:
            json.dump(log_data, f, indent=2)

    async def create_chat_completion(
        self, system_message: str, user_message: str, tool_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        conversation = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]
        if tool_config:
            return await self.create_conversation_completion(conversation, tool_config)
        else:
            return await self.create_standard_chat_completion(conversation)

    async def create_standard_chat_completion(
        self, conversation: List[Dict[str, str]], max_tokens: int = 4000
    ) -> str:
        messages = [
            {
                "role": "assistant" if msg["role"] == "system" else msg["role"],
                "content": msg["content"],
            }
            for msg in conversation
        ]

        if messages[0]["role"] != "user":
            messages.insert(0, {"role": "user", "content": "Hello!"})

        request = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        try:
            response = self.client.messages.create(**request)
            content = response.content[0].text if response.content else ""
            
            self.log_request_response(request, response.dict(), True)
            return content

        except Exception as e:
            self.logging.error(f"Error processing response content: {e}")
            self.log_request_response(request, str(e), False)
            return None
    
    async def create_conversation_completion(
        self, conversation: List[Dict[str, str]], tool_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        messages = [
            {
                "role": "assistant" if msg["role"] == "system" else msg["role"],
                "content": msg["content"],
            }
            for msg in conversation
        ]

        if messages[0]["role"] != "user":
            messages.insert(0, {"role": "user", "content": "Hello!"})

        tool = self.get_dynamic_tool(tool_config)

        request = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4000,
            "tools": [tool],
        }
        try:
            response = self.client.messages.create(**request)
            action = None
            for content_item in response.content:
                if tool_config['name'] == 'create_action':
                    if not isinstance(response.content, list):
                        if isinstance(content_item, TextBlock):
                            action = {"action" : "send_message_to_student", "params": {"message" : content_item.text}}
                            break


                # Check for ToolUseBlock
                if isinstance(content_item, ToolUseBlock):
                    if content_item.name != 'create_action':
                        if 'action' in content_item.input and 'params' in content_item.input['action']:
                            action = content_item.input['action']['action']
                            params = content_item.input['action']['params']
                            action = {"action": action, "params": params}
                        else:
                            action = {"action" : content_item.name, "params" : content_item.input}
                        break
                    elif content_item.name == 'create_action':
                        action = content_item.input['action']['action']
                        params = content_item.input['action']['params']
                        action = {"action": action, "params": params}
                    else:
                        if 'action' in content_item.input and 'params' in content_item.input['action']:
                            action = content_item.input['action']['action']
                            params = content_item.input['action']['params']
                            action = {"action": action, "params": params}
                        else:
                            action = content_item.input['action']['action']
                            params = content_item.input['action']['params']
                            action = {"action": action, "params": params}
                        break
                        

            success = action is not None
            self.log_request_response(request, response.dict(), success)
            # if tool_config['name'] == "create_action":
            #     from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
            

            if not action:
                self.logging.warning(
                    f"No valid {tool_config['name']} was generated from the LLM response."
                )
                from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()

            return action

        except Exception as e:
            self.logging.error(f"Error processing response content: {e}")
            self.log_request_response(request, str(e), False)
            return None

    def get_dynamic_tool(self, config: Dict[str, Any]):
        return {
            "name": config["name"],
            "description": config["description"],
            "input_schema": {
                "type": "object",
                "properties": {config["output_key"]: config["output_schema"]},
                "required": [config["output_key"]],
            },
        }

    def add_completion_listener(
        self, listener: Callable[[ChatCompletion], None]
    ) -> None:
        self.listeners.add(listener)

    def remove_completion_listener(
        self, listener: Callable[[ChatCompletion], None]
    ) -> None:
        self.listeners.discard(listener)

    @staticmethod
    def get_tool_config(
        tool_type: str, agent_type: str, isolated_agent: bool = False
    ) -> Dict[str, Any]:
        actions = load_actions(agent_type)
        action_names = [action["name"] for action in actions]

        isolation = ""
        if not isolated_agent and "send_message_to_student" in action_names:
            isolation = "IMPORTANT: After any action that retrieves information or performs a task, you MUST include a send_message_to_student action to communicate the results or acknowledge the completion of the task to the user."

        tool_configs = {
            "create_action": {
                "name": "create_action",
                "description": f"Create a single structured action for the AI system to execute. {isolation}",
                "output_key": "action",
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": action_names,
                            "description": "The type of action to perform",
                        },
                        "params": {
                            "type": "object",
                            "properties": {
                                action["name"]: {"type": "object"} for action in actions
                            },
                        },
                    },
                    "required": ["action", "params"],
                },
            },
            "set_goal": {
                "name": "set_goal",
                "description": "Set a goal for the AI system. Remember that any goal involving retrieving or processing information must include communicating that information to the user.",
                "output_key": "goal",
                "output_schema": {
                    "type": "string",
                    "description": "The goal to be set",
                },
            },
            "goal_check": {
                "name": "goal_check",
                "description": "Check if the current goal has been achieved. IMPORTANT: A goal is not considered fully achieved until the results or completion of tasks have been communicated to the user via a send_message_to_student action. A goal check should prevent further messages being sent to the user, i.e. if we've sent a message, it's best to wait for a response - so we should mark the goal as achieved to prevent repeated messages, as the agent will be forced to act if goal is marked as not achieved i.e. if the last agent action is send_message_to_student, we should mark the goal as achieved typically.",
                "output_key": "goal_achieved",
                "output_schema": {
                    "type": "boolean",
                    "description": "Whether the goal has been achieved",
                },
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
                            "description": "Whether the goal should be reassessed",
                        },
                        "reason": {
                            "type": "string",
                            "description": "The reason for the decision",
                        },
                    },
                    "required": ["should_reassess", "reason"],
                },
            },
            "delegate_and_execute_task": {
                "name": "delegate_and_execute_task",
                "description": "Create a structured plan for a complex task, breaking it down into levels and tasks. Remember, all tasks on a certain level execute in parallel, i.e. if a task depends on another task, they should be on separate levels. Outputs of previous levels are fed into the next level. By this I mean tasks on one level, don't have observability of outputs from other tasks on the same level. Dependencies should be on different levels. Generate with this flow in mind.",
                "output_key": "plan",
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "levels": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "order": {"type": "integer"},
                                    "tasks": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "description": {"type": "string"},
                                                "agent_type": {"type": "string"},
                                            },
                                            "required": [
                                                "name",
                                                "description",
                                                "agent_type",
                                            ],
                                        },
                                    },
                                },
                                "required": ["order", "tasks"],
                            },
                        }
                    },
                    "required": ["levels"],
                },
            },
        }
        return tool_configs.get(tool_type, {})
