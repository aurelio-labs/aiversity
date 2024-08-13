import logging
from typing import Dict, List, Tuple, Any
from ARCANE.agent_prompting.agent_prompts import generate_agent_prompt
from ARCANE.actions.file_manipulation import SendNIACLMessage
from channels.web.agent_communication_channel import AgentCommunicationChannel
from llm.LLM import LLM
from ARCANE.arcane_architecture import ArcaneArchitecture, Event, GlobalEventLog
from channels.communication_channel import CommunicationChannel
import os
import asyncio
from collections import deque


class ArcaneSystem:
    def __init__(
        self,
        name: str,
        llm: LLM,
        model: str,
        logger: logging.Logger,
        port: int,
        agent_config: dict,
        common_actions: List[Dict],
        api_key,
        agent_factory,
    ):
        self.name = name
        self.llm = llm
        self.model = model
        self.logger = logger
        self.agent_id = agent_config["id"]
        self.agent_config = agent_config
        self.common_actions = common_actions
        self.agent_prompt = generate_agent_prompt(agent_config)
        self.agent_factory = agent_factory
        self.arcane_architecture = ArcaneArchitecture(
            self.llm,
            self.logger,
            self.agent_id,
            self.agent_prompt,
            self.agent_config,
            self,
            self.agent_factory,
        )
        self.allowed_communications = agent_config["allowed_communications"]
        self.message_queue = deque(maxlen=100)  # Limit to last 100 messages

        self.status = "idle"
        # if self.agent_id == "stratos-5001":
        #     self.status = "busy"
        self.current_action = None
        self.responsive_llm = LLM(logger, api_key, os.getenv("CLAUDE_RESPONSIVE_MODEL"))

    async def log_file_addition(self, file_name: str):
        print(f"Logging file addition: {file_name}")
        event = Event("file_added", {"file_name": file_name})
        self.arcane_architecture.global_event_log.add_event(event, self.agent_id)

    async def log_file_deletion(self, file_name: str):
        print(f"Logging file deletion: {file_name}")  # Debug print
        event = Event("file_deleted", {"file_name": file_name})
        self.arcane_architecture.global_event_log.add_event(event, self.agent_id)

    async def set_status(self, status: str, action_description: str = None):
        self.status = status
        self.current_action = action_description
        self.logger.info(f"Agent {self.name} status: {status} - {action_description}")

    async def unset_busy_status(self):
        await self.set_status("idle")
        self.current_action = None
        self.logger.info(f"Agent {self.name} is now idle")

    async def get_status_response(self, sender: str) -> str:
        # self.current_action = "GENERATING EXAM PAPER"
        prompt = f"""
        I am the quick response system for {self.name}, a submodule for an AI agent in the AIversity system. {self.name} is currently {self.status}.
        If I am busy, my current action is: {self.current_action}.
        Agent {sender} is trying to communicate with me.
        I will provide a brief, polite response explaining my current status.
        I will keep the response under 50 words.
        """
        tool_config = self.responsive_llm.get_tool_config("create_action")
        response = await self.responsive_llm.create_chat_completion(
            prompt,
            "Provide an NIACL response now. You should communicate via send_niacl_message.",
            tool_config,
        )

        if response and isinstance(response, list) and len(response) > 0:
            niacl_message = response[0]["actions"][0]["params"]["message"]

            # Create and send NIACL message asynchronously
            send_niacl = SendNIACLMessage(
                receiver=sender,
                message=niacl_message,
                sender=self.agent_id,
                agent_config=self.agent_config,
            )
            asyncio.create_task(send_niacl.execute())

            return f"NIACL message sent asynchronously to {sender}. The agent will continue its current task and will be notified when a response is received."
        else:
            return "Unable to generate a response. The agent will continue its current task."

    async def process_incoming_user_message(
        self, communication_channel: CommunicationChannel, user_id: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        try:
            message = await communication_channel.get_last_message()
            narrative, actions = await self.arcane_architecture.process_message(
                user_id, message, communication_channel
            )

            print(f"Processed message for {user_id}. Actions taken: {len(actions)}")

            return narrative, actions
        except Exception as e:
            await self.handle_error(e, user_id, communication_channel)
            return f"An error occurred: {str(e)}", []

    async def process_incoming_agent_message(
        self, sender: str, message: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        self.message_queue.append((sender, message))
        if self.status == "busy":
            status_response = await self.get_status_response(sender)
            return status_response, []
        try:
            # from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
            communication_channel = AgentCommunicationChannel(sender, message, self)
            narrative, actions = await self.arcane_architecture.process_message(
                sender, message, communication_channel
            )

            print(
                f"Processed agent message from {sender}. Actions taken: {len(actions)}"
            )

            return narrative, actions
        except Exception as e:
            print(f"Error processing agent message: {str(e)}")
            return f"An error occurred: {str(e)}", []

    async def log_agent_message(self, sender: str, message: str):
        # Remove the event logging from here - was causing duplicate messages
        # event = Event("agent_message", {"sender": sender, "content": message})
        # self.arcane_architecture.global_event_log.add_event(event)

        # Keep only the print statement
        print(f"Received message from {sender}: {message[:50]}...")

    async def log_agent_message_processing(
        self, sender_id: str, narrative: str, actions: List[Dict[str, Any]]
    ):
        event = Event(
            "agent_message_processed",
            {"narrative": narrative, "actions": actions, "sender_id": sender_id},
        )
        self.arcane_architecture.global_event_log.add_event(event, self.agent_id)

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

    async def handle_error(
        self,
        error: Exception,
        user_id: str,
        communication_channel: CommunicationChannel,
    ) -> None:
        await self.arcane_architecture.handle_error(
            error, user_id, communication_channel
        )

    def get_available_actions(self) -> List[str]:
        return [
            action["action"]
            for action in self.common_actions + self.agent_config["specific_actions"]
        ]

    async def evaluate_task_progress(self, response: str) -> Dict[str, Any]:
        prompt = f"""
        You are a Stratos clone overseeing a task. You've received the following response from an agent:

        {response}

        Evaluate whether the task is complete based on this response. If it's not complete, provide feedback for the agent.

        Your evaluation should be in the following format:
        {{
            "is_complete": boolean,
            "feedback": "Your feedback here if not complete, or 'Task completed successfully' if complete"
        }}
        """

        tool_config = self.llm.get_tool_config("create_action", self.agent_id)
        evaluation_response = await self.llm.create_chat_completion(
            self.agent_prompt, prompt, tool_config
        )

        if (
            evaluation_response
            and isinstance(evaluation_response, list)
            and len(evaluation_response) > 0
        ):
            return evaluation_response[0]
        else:
            return {
                "is_complete": False,
                "feedback": "Unable to evaluate task progress. Please provide more information.",
            }

    def has_new_message(self) -> bool:
        return len(self.message_queue) > 0

    def get_latest_message(self) -> str:
        if self.has_new_message():
            return self.message_queue.popleft()[1]
        return None
