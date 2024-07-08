import logging
from typing import Dict, List, Tuple, Any
from llm.LLM import LLM
from ARCANE.arcane_architecture import ArcaneArchitecture, Event, EventLog
from channels.communication_channel import CommunicationChannel

class ArcaneSystem:
    def __init__(self, name: str, llm: LLM, model: str, logger: logging.Logger, port: int):
        self.name = name
        self.llm = llm
        self.model = model
        self.logger = logger
        self.agent_id = f"{name}-{port}"
        self.arcane_architecture = ArcaneArchitecture(self.llm, self.logger, self.agent_id)

    async def process_incoming_user_message(self, communication_channel: CommunicationChannel, user_id: str) -> Tuple[str, List[Dict[str, Any]]]:
        try:
            message = await communication_channel.get_last_message()
            await self.arcane_architecture.process_message(user_id, message, communication_channel)
            
            # Retrieve the updated event log
            event_log = self.arcane_architecture.get_event_log(user_id)
            
            # Extract the narrative and actions from the event log
            narrative = event_log.to_narrative()
            actions = [event.data for event in event_log.events if event.type == "agent_action"]
            
            return narrative, actions
        except Exception as e:
            await self.arcane_architecture.handle_error(e, user_id, communication_channel)
            return f"An error occurred: {str(e)}", []

    async def start(self) -> None:
        self.logger.info(f"Starting {self.name} ArcaneSystem")
        # Any additional initialization code can go here

    async def shutdown(self) -> None:
        self.logger.info(f"Shutting down {self.name} ArcaneSystem")
        await self.arcane_architecture.shutdown()
        # Add any additional cleanup code here

    def get_event_log(self, user_id: str) -> EventLog:
        return self.arcane_architecture.get_event_log(user_id)

    def clear_event_log(self, user_id: str) -> None:
        self.arcane_architecture.clear_event_log(user_id)

    async def handle_error(self, error: Exception, user_id: str, communication_channel: CommunicationChannel) -> None:
        await self.arcane_architecture.handle_error(error, user_id, communication_channel)