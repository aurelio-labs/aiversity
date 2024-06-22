from ARCANE.action_layer import ActionLayer
from llm.LLM import LLM

class ArcaneSystem:
    def __init__(self, name, llm: LLM, model: str, logger):
        self.name = name
        self.llm = llm
        self.model = model

        self.action_agent: ActionLayer = ActionLayer(
            name,
            llm,
            model,
            logger
        )


    async def process_incoming_user_message(self, communication_channel):
        await self.action_agent.process_incoming_user_message(communication_channel=communication_channel)

    async def start(self):
        import time