from ARCANE.action_layer import ActionLayer
from llm.LLM import LLM
from typing import Dict, List
from ARCANE.types import ChatMessage, create_chat_message

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

    async def process_incoming_user_message(self, communication_channel, user_id: str):
        if user_id not in self.chat_histories:
            self.chat_histories[user_id] = []

        new_message = create_chat_message("user", await communication_channel.get_last_message())
        self.chat_histories[user_id].append(new_message)

        self.prune_chat_history(user_id)

        response = await self.action_agent.process_incoming_user_message(
            communication_channel=communication_channel,
            chat_history=self.chat_histories[user_id]
        )

        if response:  # Only send and add to history if there's a response
            await communication_channel.send_message(response)
            agent_message = create_chat_message(self.name, response)
            self.chat_histories[user_id].append(agent_message)

    def prune_chat_history(self, user_id: str, max_messages: int = 10):
        """Keep only the last `max_messages` in the chat history."""
        if len(self.chat_histories[user_id]) > max_messages:
            self.chat_histories[user_id] = self.chat_histories[user_id][-max_messages:]

    async def start(self):
        # Any initialization code can go here
        pass