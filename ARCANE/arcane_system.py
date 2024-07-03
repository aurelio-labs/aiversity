from ARCANE.action_layer import ActionLayer
from llm.LLM import LLM
from typing import Dict, List
from ARCANE.types import ChatMessage, create_chat_message
from ARCANE.arcane_architecture import ArcaneArchitecture
import json

class ArcaneSystem:
    def __init__(self, name, llm: LLM, model: str, logger):
        self.name = name
        self.llm = llm
        self.model = model
        self.logger = logger

        self.action_agent: ActionLayer = ActionLayer(
            name,
            llm,
            model,
            logger
        )

        # New: Dictionary to store chat histories
        self.chat_histories: Dict[str, List[ChatMessage]] = {}

        self.arcane_architecture = ArcaneArchitecture(self.llm, self.logger)

    async def process_incoming_user_message(self, communication_channel, user_id: str):
        if user_id not in self.chat_histories:
            self.chat_histories[user_id] = []

        new_message = create_chat_message("user", await communication_channel.get_last_message())
        self.chat_histories[user_id].append(new_message)

        self.prune_chat_history(user_id)

        plan, actions = await self.arcane_architecture.process_message(user_id, self.chat_histories[user_id], communication_channel)

        # Send actions to the frontend
        await communication_channel.send_actions(actions)

        return plan, actions

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

    def prune_chat_history(self, user_id: str, max_messages: int = 10):
        """Keep only the last `max_messages` in the chat history."""
        if len(self.chat_histories[user_id]) > max_messages:
            self.chat_histories[user_id] = self.chat_histories[user_id][-max_messages:]

    async def start(self):
        # Any initialization code can go here
        pass