import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import logging
import importlib
import json
from llm.LLM import LLM
from channels.communication_channel import CommunicationChannel
import ARCANE.agent_prompting.static.triage_prompts as prompts
from ARCANE.actions.action import Action
from ARCANE.actions.triage_agent_actions import SendMessageToStudent
from ARCANE.actions.file_manipulation import ViewFileContents, EditFileContents, CreateNewFile, RunPythonFile, QueryFileSystem
from ARCANE.actions.send_message_to_spaceship import SendMessageToSpaceship

class Event:
    def __init__(self, event_type: str, data: Dict[str, Any], timestamp: Optional[datetime] = None):
        self.id = str(uuid.uuid4())
        self.type = event_type
        self.data = data
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }

class EventLog:
    def __init__(self):
        self.events: List[Event] = []

    def add_event(self, event: Event):
        self.events.append(event)

    def get_recent_events(self, n: int) -> List[Event]:
        return sorted(self.events, key=lambda e: e.timestamp, reverse=True)[:n]

    def to_narrative(self) -> str:
        narrative = []
        for event in sorted(self.events, key=lambda e: e.timestamp):
            if event.type == "user_message":
                narrative.append(f"[{event.timestamp}] User: {event.data['content']}")
            elif event.type == "agent_action":
                action_data = json.dumps(event.data, indent=2)
                narrative.append(f"[{event.timestamp}] Agent action:\n{action_data}")
            elif event.type == "goal_set":
                narrative.append(f"[{event.timestamp}] Goal set: {event.data['goal']}")
        return "\n".join(narrative)

class ArcaneArchitecture:
    def __init__(self, llm: LLM, logger: logging.Logger, agent_id: str):
        self.llm = llm
        self.logger = logger
        self.agent_id = agent_id
        self.event_logs: Dict[str, EventLog] = {}
        self.prompts = prompts
        importlib.reload(prompts)


    #from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()

    async def process_message(self, user_id: str, message: str, communication_channel: CommunicationChannel) -> Tuple[str, List[Dict[str, Any]]]:
        if user_id not in self.event_logs:
            self.event_logs[user_id] = EventLog()

        self.event_logs[user_id].add_event(Event("user_message", {"content": message}))

        goal = await self.generate_initial_goal(user_id)
        self.event_logs[user_id].add_event(Event("goal_set", {"goal": goal}))

        executed_actions = []
        # from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
        while not await self.goal_achieved(goal, executed_actions, user_id):
            narrative = self.event_logs[user_id].to_narrative()
            next_action = await self.determine_next_action(goal, executed_actions, user_id)

            if next_action and isinstance(next_action, list) and len(next_action) > 0:
                action_data = next_action[0]  # Take only the first action
                action_data = action_data['actions'][0]
                self.event_logs[user_id].add_event(Event("agent_action", action_data))
                
                try:
                    success, result = await self.execute_action(action_data, communication_channel)
                    executed_actions.append({"action": action_data, "success": success, "result": result})
                    
                    # if action_data['action'] == 'send_message_to_student':
                    #     self.event_logs[user_id].add_event(Event("agent_message", {"content": action_data['params']['message']}))
                except Exception as e:
                    self.logger.error(f"Error executing action: {str(e)}")
                    executed_actions.append({"action": action_data, "success": False, "error": str(e)})
                    await communication_channel.send_message(f"An error occurred while processing your request: {str(e)}")
            else:
                self.logger.warning("No valid action determined. Ending process.")
                await communication_channel.send_message("I'm having trouble determining the next step. Could you please provide more information or clarify your request?")
                break

        return self.event_logs[user_id].to_narrative(), executed_actions

    async def generate_initial_goal(self, user_id: str) -> str:
        goal_prompt = self.create_goal_prompt(self.event_logs[user_id].to_narrative())
        tool_config = self.llm.get_tool_config("set_goal")
        goal_response = await self.llm.create_chat_completion(goal_prompt, self.get_last_user_message(user_id), tool_config)
        
        if goal_response and isinstance(goal_response, list) and len(goal_response) > 0:
            if isinstance(goal_response[0], dict):
                return goal_response[0].get('goal', '')
            elif isinstance(goal_response[0], str):
                return goal_response[0]
        
        self.logger.warning("Failed to generate a valid goal. Using default.")
        return "Assist the user with their query"

    async def goal_achieved(self, goal: str, actions: List[Dict], user_id: str) -> bool:
        goal_check_prompt = self.create_goal_check_prompt(goal, actions, self.event_logs[user_id].to_narrative())
        tool_config = self.llm.get_tool_config("goal_check")
        goal_check_response = await self.llm.create_chat_completion(goal_check_prompt, json.dumps(actions), tool_config)
        
        if goal_check_response and isinstance(goal_check_response, list) and len(goal_check_response) > 0:
            if isinstance(goal_check_response[0], dict):
                return goal_check_response[0].get('goal_achieved', False)
            elif isinstance(goal_check_response[0], bool):
                return goal_check_response[0]
        
        return False

    async def determine_next_action(self, goal: str, actions: List[Dict], user_id: str) -> List[Dict[str, Any]]:
        action_prompt = self.create_action_prompt(goal, actions, self.event_logs[user_id].to_narrative())
        tool_config = self.llm.get_tool_config("create_action")
        action_response = await self.llm.create_chat_completion(action_prompt, self.get_last_user_message(user_id), tool_config)
        
        if action_response and isinstance(action_response, list) and len(action_response) > 0:
            return action_response
        
        self.logger.warning("Failed to determine next action. Using default.")
        return [{"action": "send_message_to_student", "params": {"message": "I'm not sure how to proceed. Can you provide more information?"}}]

    async def execute_action(self, action_data: Dict[str, Any], communication_channel: CommunicationChannel) -> Tuple[bool, Any]:
        action = self.parse_action(communication_channel, action_data)
        if action is None:
            self.logger.warning(f"Unknown action: {action_data}")
            action = SendMessageToStudent(
                communication_channel,
                f"I encountered an error while processing the action: {action_data.get('action')}. Could you please rephrase or provide more details?"
            )
        return await action.execute()

    def parse_action(self, communication_channel: CommunicationChannel, action_data: dict) -> Optional[Action]:
        action_name = action_data.get("action")
        params = action_data.get("params", {})
        
        try:
            if action_name == "send_message_to_student":
                return SendMessageToStudent(communication_channel=communication_channel, message=params.get("message", ""))
            elif action_name == "query_file_system":
                return QueryFileSystem(command=params.get("command", ""), agent_id=self.agent_id)
            elif action_name == "view_file_contents":
                return ViewFileContents(file_path=params.get("file_path", ""), agent_id=self.agent_id)
            elif action_name == "edit_file_contents":
                return EditFileContents(file_path=params.get("file_path", ""), content=params.get("content", ""), agent_id=self.agent_id)
            elif action_name == "create_new_file":
                return CreateNewFile(file_path=params.get("file_path", ""), agent_id=self.agent_id)
            elif action_name == "run_python_file":
                return RunPythonFile(file_path=params.get("file_path", ""), agent_id=self.agent_id)
            elif action_name == "send_message_to_spaceship":
                return SendMessageToSpaceship(message=params.get("message", ""))
            else:
                self.logger.warning(f"Unknown action: {action_name}")
                return None
        except KeyError as e:
            self.logger.error(f"Missing required parameter for action {action_name}: {str(e)}")
            return None

    def get_last_user_message(self, user_id: str) -> str:
        for event in reversed(self.event_logs[user_id].events):
            if event.type == "user_message":
                return event.data.get('content', '')
        return ""

    def create_goal_prompt(self, narrative: str) -> str:
        context = self.create_system_message()
        return f"""
        {context}

        You are an AI assistant tasked with setting a goal to address the user's latest message.
        Given the following narrative of events, determine an appropriate goal.

        Narrative:
        ========
        {narrative}
        ========

        Determine a goal that addresses the user's needs based on the context and narrative.
        """

    def create_action_prompt(self, goal: str, actions: List[Dict], narrative: str) -> str:
        context = self.create_system_message()
        action_log_str = json.dumps(actions, indent=2)
        return f"""
        {context}

        You are an AI assistant tasked with determining the next action to take towards achieving a goal.
        Given the following context, goal, action history, and narrative of events, decide on the next action.

        Goal:
        ========
        {goal}
        ========

        Action History:
        ========
        {action_log_str}
        ========

        Narrative:
        ========
        {narrative}
        ========

        Determine the next action to take to achieve the goal. Remember to communicate any retrieved information or completed tasks to the user.
        """

    def create_goal_check_prompt(self, goal: str, actions: List[Dict], narrative: str) -> str:
        context = self.create_system_message()
        action_log_str = json.dumps(actions, indent=2)
        return f"""
        {context}

        You are an AI assistant tasked with determining if a goal has been achieved.
        Given the following context, goal, action history, and narrative of events, decide if the goal has been achieved.

        Goal:
        ========
        {goal}
        ========

        Action History:
        ========
        {action_log_str}
        ========

        Narrative:
        ========
        {narrative}
        ========

        Determine whether the goal has been achieved based on the actions taken and the current state of the conversation.
        Remember that the goal is not considered fully achieved until the results or completion of tasks have been communicated to the user.
        """

    def create_system_message(self) -> str:
        return f"""
        {self.prompts.situational_context}
        {self.prompts.self_identity}
        {self.prompts.personality}
        {self.prompts.knowledge}
        {self.prompts.actions}
        
        IMPORTANT: After any action that retrieves information or performs a task, you MUST include a send_message_to_student action to communicate the results or acknowledge the completion of the task to the user. The user cannot see the results of your actions directly and relies on your messages to stay informed.
        """

    def get_event_log(self, user_id: str) -> EventLog:
        return self.event_logs.get(user_id, EventLog())

    def clear_event_log(self, user_id: str) -> None:
        if user_id in self.event_logs:
            self.event_logs[user_id] = EventLog()

    # async def handle_error(self, error: Exception, user_id: str, communication_channel: CommunicationChannel) -> None:
    #     error_message = f"An error occurred: {str(error)}"
    #     self.logger.error(error_message)
    #     await communication_channel.send_message(error_message)
    #     self.clear_event_log(user_id)

    async def shutdown(self) -> None:
        self.logger.info("Shutting down ArcaneArchitecture")
        # Add any cleanup code here, such as saving state or closing connections