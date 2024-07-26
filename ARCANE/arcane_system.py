import logging
from typing import Dict, List, Tuple, Any
from ARCANE.agent_prompting.agent_prompts import generate_agent_prompt
from channels.web.agent_communication_channel import AgentCommunicationChannel
from llm.LLM import LLM
from ARCANE.arcane_architecture import ArcaneArchitecture, Event, GlobalEventLog
from channels.communication_channel import CommunicationChannel

class ArcaneSystem:
    def __init__(self, name: str, llm: LLM, model: str, logger: logging.Logger, port: int, agent_config: dict):
        self.name = name
        self.llm = llm
        self.model = model
        self.logger = logger
        self.agent_id = f"{name}-{port}"
        self.agent_prompt = generate_agent_prompt(agent_config)
        self.arcane_architecture = ArcaneArchitecture(self.llm, self.logger, self.agent_id, self.agent_prompt, agent_config)
        self.agent_config = agent_config
        self.allowed_communications = []

    async def process_incoming_user_message(self, communication_channel: CommunicationChannel, user_id: str) -> Tuple[str, List[Dict[str, Any]]]:
        try:
            message = await communication_channel.get_last_message()
            narrative, actions = await self.arcane_architecture.process_message(user_id, message, communication_channel)
            
            print(f"Processed message for {user_id}. Actions taken: {len(actions)}")
            
            return narrative, actions
        except Exception as e:
            await self.handle_error(e, user_id, communication_channel)
            return f"An error occurred: {str(e)}", []

    async def process_incoming_agent_message(self, sender: str, message: str) -> Tuple[str, List[Dict[str, Any]]]:
        try:
            # from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
            communication_channel = AgentCommunicationChannel(sender, message, self)
            narrative, actions = await self.arcane_architecture.process_message(sender, message, communication_channel)
            
            print(f"Processed agent message from {sender}. Actions taken: {len(actions)}")
            
            return narrative, actions
        except Exception as e:
            print(f"Error processing agent message: {str(e)}")
            return f"An error occurred: {str(e)}", []

    async def log_agent_message(self, sender: str, message: str):
        event = Event("agent_message", {"sender": sender, "content": message})
        self.arcane_architecture.global_event_log.add_event(event)
        
        # Log the one-liner
        print(f"Received message from {sender}: {message[:50]}...")
        

    async def log_agent_message_processing(self, sender_id: str, narrative: str, actions: List[Dict[str, Any]]):
        event = Event("agent_message_processed", {"narrative": narrative, "actions": actions, "sender_id": sender_id})
        self.arcane_architecture.global_event_log.add_event(event)

    async def start(self) -> None:
        self.logger.info(f"Starting {self.name} ArcaneSystem")
        # Any additional initialization code can go here

    async def shutdown(self) -> None:
        self.logger.info(f"Shutting down {self.name} ArcaneSystem")
        await self.arcane_architecture.shutdown()
        # Add any additional cleanup code here

    def get_event_log(self) -> GlobalEventLog:
        return self.arcane_architecture.global_event_log

    def clear_event_log(self):
        self.arcane_architecture.global_event_log = GlobalEventLog()

    async def handle_error(self, error: Exception, user_id: str, communication_channel: CommunicationChannel) -> None:
        await self.arcane_architecture.handle_error(error, user_id, communication_channel)