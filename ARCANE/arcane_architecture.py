import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import logging
import importlib
import json
from util import get_environment_variable
from llm.LLM import LLM
from channels.communication_channel import CommunicationChannel
import ARCANE.agent_prompting.agent_prompts as prompts
from ARCANE.actions.action import Action
from ARCANE.actions.triage_agent_actions import SendMessageToStratos, SendMessageToStudent
from ARCANE.actions.file_manipulation import ViewFileContents, EditFileContents, CreateNewFile, RunPythonFile, QueryFileSystem, VisualizeImage
from ARCANE.actions.send_message_to_spaceship import SendMessageToSpaceship
from ARCANE.actions.file_manipulation import SendNIACLMessage
from ARCANE.actions.task_agent_actions import PerplexitySearch, DeclareComplete, CreateFile, ReadFile

from ARCANE.planning.stratos_planning import DelegateAndExecuteTask
import os

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

class GlobalEventLog:
    def __init__(self):
        self.events: List[Event] = []

    def add_event(self, event: Event, agent_id: str):
        self.events.append(event)
        print(f"{agent_id} -> Added event: {event.type} - {event.data}")

    def get_recent_events(self, n: int) -> List[Event]:
        return sorted(self.events, key=lambda e: e.timestamp, reverse=True)[:n]

    def to_narrative(self) -> str:
        narrative = []
        for event in sorted(self.events, key=lambda e: e.timestamp):
            if event.type == "user_message":
                narrative.append(f"[{event.timestamp}] User: {event.data['content']}")
            elif event.type == "agent_message":
                sender = event.data.get('sender', 'Unknown Agent')
                narrative.append(f"[{event.timestamp}] Agent {sender}: {event.data['content']}")
            elif event.type == "agent_action":
                action_data = json.dumps(event.data, indent=2)
                narrative.append(f"[{event.timestamp}] Agent action:\n{action_data}")
            elif event.type == "goal_set":
                narrative.append(f"[{event.timestamp}] Goal set: {event.data['goal']}")
            elif event.type == "task_execution":
                narrative.append(f"[{event.timestamp}] Task Execution:\n{event.data['content']}. Results may still need to be communicated with agents that requested this task.")
            elif event.type == "file_added":
                narrative.append(f"[{event.timestamp}] User added file to workspace: {event.data['file_name']}")
            elif event.type == "file_deleted":
                narrative.append(f"[{event.timestamp}] File deleted from workspace: {event.data['file_name']}")
        
        return "\n".join(narrative)

class ArcaneArchitecture:
    def __init__(self, llm: LLM, logger: logging.Logger, agent_id: str, agent_prompt: str, agent_config: dict, arcane_system, agent_factory):
        self.llm = llm
        self.logger = logger
        self.agent_id = agent_id
        self.agent_prompt = agent_prompt
        self.global_event_log = GlobalEventLog()
        self.prompts = prompts
        self.agent_config = agent_config
        self.arcane_system = arcane_system
        self.agent_factory = agent_factory
        importlib.reload(prompts)
        self.is_core_agent = agent_id in ['iris-5000', 'stratos-5001']


    async def send_niacl_message(self, receiver: str, message: str) -> Tuple[bool, str]:
        action = SendNIACLMessage(receiver, message, self.agent_id, self.agent_config)
        return await action.execute()

    async def generate_initial_goal(self) -> str:
        narrative = self.global_event_log.to_narrative()
        last_message = self.get_last_message_from_log()
        
        goal_prompt = self.create_goal_prompt(narrative)
        tool_config = self.llm.get_tool_config("set_goal", self.agent_config['name'])
        goal_response = await self.llm.create_chat_completion(goal_prompt, last_message, tool_config)
        
        if goal_response and isinstance(goal_response, list) and len(goal_response) > 0:
            if isinstance(goal_response[0], dict):
                return goal_response[0].get('goal', '')
            elif isinstance(goal_response[0], str):
                return goal_response[0]
        
        self.logger.warning("Failed to generate a valid goal. Using default.")
        return "Process the message and respond appropriately"

    def get_last_message_from_log(self) -> str:
        for event in reversed(self.global_event_log.events):
            if event.type in ["user_message", "agent_message"]:
                return event.data.get('content', '')
        return ""

    def create_goal_prompt(self, narrative: str) -> str:
        context = self.create_system_message()
        return f"""
        {context}

        SYSTEM: You are a specialized goal-setting module within the AIversity system. Your sole purpose is to analyze the provided narrative and determine an appropriate goal based on the user's request or the current situation.

        IMPORTANT INSTRUCTIONS:
        1. You must use ONLY the set_goal tool to define the goal.
        2. Do NOT suggest or describe actions to be taken. Your role is strictly to set a goal.
        3. The goal should be concise but descriptive, capturing the main objective based on the narrative.
        4. The goal should be actionable and clear for other parts of the system to work with.

        NARRATIVE OF EVENTS:
        {narrative}

        TASK:
        Carefully analyze the narrative and determine an appropriate goal that addresses the user's request or the current situation.

        RESPONSE FORMAT:
        Use ONLY the set_goal tool to define the goal. Do not include any other text or explanations in your response.
        """

    async def goal_achieved(self, goal: str, actions: List[Dict]) -> bool:
        narrative = self.global_event_log.to_narrative()
        goal_check_prompt = self.create_goal_check_prompt(goal, narrative)
        tool_config = self.llm.get_tool_config("goal_check", self.agent_id)
        # from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
        user_message = f"""
            Here is the goal:
            ========
            Current goal: {goal}
            ========

            Here is the current narrative:
            ========
            {narrative}
            ========

            Judge based on the above narrative...
            """
        goal_check_response = await self.llm.create_chat_completion(goal_check_prompt, narrative, tool_config)
        
        if goal_check_response and isinstance(goal_check_response, list) and len(goal_check_response) > 0:
            if isinstance(goal_check_response[0], dict):
                achieved = goal_check_response[0].get('goal_achieved', False)
            elif isinstance(goal_check_response[0], bool):
                achieved = goal_check_response[0]
            else:
                achieved = False
            
            print(f"Goal check: {'Achieved' if achieved else 'Not Achieved'}")
            return achieved
        
        return False

    async def process_message(self, sender_id: str, message: str, communication_channel: CommunicationChannel) -> Tuple[str, List[Dict[str, Any]]]:
        # Determine if the sender is a user or an agent
        event_type = "user_message" if sender_id.startswith("user_") else "agent_message"
        event_data = {"content": message, "sender": sender_id}
        
        # Add the incoming message to the global event log
        self.global_event_log.add_event(Event(event_type, event_data), self.agent_id)

        # Generate the initial goal
        goal = await self.generate_initial_goal()
        self.global_event_log.add_event(Event("goal_set", {"goal": goal}), self.agent_id)

        executed_actions = []
        max_iterations = 5  # Limit the number of iterations to prevent infinite loops

        for _ in range(max_iterations):
            if await self.goal_achieved(goal, executed_actions):
                break

            narrative = self.global_event_log.to_narrative()
            next_action = await self.determine_next_action(goal, executed_actions)

            if next_action and isinstance(next_action, list) and len(next_action) > 0:
                action_data = next_action[0]['actions'][0]
                self.global_event_log.add_event(Event("agent_action", action_data), self.agent_id)
                
                try:
                    success, result = await self.execute_action(action_data, communication_channel)
                    executed_actions.append({"action": action_data, "success": success, "result": result})
                except Exception as e:
                    self.logger.error(f"Error executing action: {str(e)}")
                    executed_actions.append({"action": action_data, "success": False, "error": str(e)})
                    await communication_channel.send_message(f"An error occurred while processing your request: {str(e)}")
            else:
                self.logger.warning("No valid action determined. Ending process.")
                await communication_channel.send_message("I'm having trouble determining the next step. Could you please provide more information or clarify your request?")
                break

        return self.global_event_log.to_narrative(), executed_actions

    async def determine_next_action(self, goal: str, actions: List[Dict]) -> List[Dict[str, Any]]:
        action_prompt = self.create_action_prompt(goal, actions, self.global_event_log.to_narrative())
        tool_config = self.llm.get_tool_config("create_action", agent_type=self.agent_id.split('-')[0])
        action_response = await self.llm.create_chat_completion(action_prompt, self.get_last_message_from_log(), tool_config)
        
        if action_response and isinstance(action_response, list) and len(action_response) > 0:
            return action_response
        
        self.logger.warning("Failed to determine next action. Using default.")
        return [{"action": "send_message_to_student", "params": {"message": "I'm not sure how to proceed. Can you provide more information?"}}]


    async def execute_action(self, action_data: Dict[str, Any], communication_channel: CommunicationChannel) -> Tuple[bool, Any]:
        action = self.parse_action(communication_channel, action_data)
        if action is None:
            self.logger.warning(f"Unknown action: {action_data}")
            return False, "Unknown action"
        
        action_description = f"Executing {action_data['action']}"
        await self.arcane_system.set_status("busy", action_description)
        
        try:
            success, result = await action.execute()
        finally:
            await self.arcane_system.unset_busy_status()

        if isinstance(action, DelegateAndExecuteTask) and success:
            self.global_event_log.add_event(Event("task_execution", {"content": result}), self.agent_id)
    
        
        if action_data['action'] != 'send_message_to_student' and communication_channel is not None:
            brief_result = str(result)[:50] if result else "No result"
            await self.send_execution_update(communication_channel, action_data['action'], brief_result)
        
        return success, result

    def parse_action(self, communication_channel: CommunicationChannel, action_data: dict) -> Optional[Action]:
        action_name = action_data.get("action")
        params = action_data.get("params", {})
        
        working_directory = self.agent_config.get("work_directory", "")
        action_map = {
            "run_command": lambda: QueryFileSystem(command=params.get("command", ""), work_directory=working_directory),
            "view_file_contents": lambda: ViewFileContents(file_path=params.get("file_path", ""), work_directory=working_directory),
            "edit_file_contents": lambda: EditFileContents(file_path=params.get("file_path", ""), content=params.get("content", ""), work_directory=working_directory),
            "create_new_file": lambda: CreateNewFile(file_path=params.get("file_path", ""), work_directory=working_directory, content=params.get("contents", "")),
            "run_python_file": lambda: RunPythonFile(file_path=params.get("file_path", ""), work_directory=working_directory),
            "perplexity_search": lambda: PerplexitySearch(query=params.get("query", ""), api_key=get_environment_variable('PERPLEXITY_API_KEY')),
            "send_message_to_student": lambda: SendMessageToStudent(communication_channel=communication_channel, message=params.get("message", "")),
            "send_niacl_message": lambda: SendNIACLMessage(receiver=params.get("receiver", ""), message=params.get("message", ""), sender=self.agent_id, agent_config=self.agent_config),
            "delegate_and_execute_task": lambda: DelegateAndExecuteTask(plan_name=params.get("task_name", "Unnamed Task"), plan_description=params.get("task_description", "No Description Given"), agent_id=self.agent_id, llm=self.llm, agent_factory=self.agent_factory, stratos=self.arcane_system, logger=self.logger),
            "declare_complete": lambda: DeclareComplete(agent_id=self.agent_id, message=params.get("message", ""), files=params.get("files", []), work_directory=working_directory),
            "visualize_image": lambda: VisualizeImage(file_path=params.get("file_path", ""), work_directory=working_directory)
        }
        
        if action_name in action_map:
            return action_map[action_name]()
        else:
            self.logger.warning(f"Unknown action: {action_name}")
            return None

    def get_last_message(self, sender_id: str) -> str:
        for event in reversed(self.global_event_log.events):
            if event.type in ["user_message", "agent_message"]: 
                return event.data.get('content', '')
        return ""


    def create_action_prompt(self, goal: str, actions: List[Dict], narrative: str) -> str:
        context = self.create_system_message()
        action_log_str = json.dumps(actions, indent=2)
        return f"""
        {context}

        I am an AI assistant tasked with determining the next action to take towards achieving a goal.
        Given the following context, goal, action history, and narrative of events, I will decide on the next action.

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

        I will determine the next action to take to achieve the goal. I will remember to communicate any retrieved information or completed tasks to the user.
        """

    def create_goal_check_prompt(self, goal: str, narrative: str) -> str:
        context = self.create_system_message()
        return f"""
        {context}

        SYSTEM: You are a specialized goal achievement verification module within the AIversity system. Your sole purpose is to analyze the provided narrative and determine if the specified goal has been achieved based ONLY on the actions and events described in the narrative. 

        IMPORTANT GUIDELINES:
        1. You are NOT an action-taking agent in this context. You are an observer and analyst only.
        2. Do NOT suggest or describe actions to be taken. Your role is strictly to evaluate past actions.
        3. The narrative represents all actions that have actually occurred. Anything not in the narrative has not happened.
        4. A goal is only considered achieved if there is explicit evidence in the narrative that all required actions have been completed AND their outcomes have been properly communicated or acknowledged.
        5. Intentions, plans, or descriptions of future actions do NOT count as achievement. Only completed actions matter.
        6. If the narrative doesn't clearly indicate goal completion, the goal is NOT achieved.

        GOAL TO VERIFY:
        {goal}

        NARRATIVE OF EVENTS:
        {narrative}

        TASK:
        Carefully analyze the narrative and determine if the goal has been achieved based SOLELY on the actions and events described.

        RESPONSE FORMAT:
        Respond ONLY with the goal_check tool, providing a boolean value:
        - true if the goal is definitively achieved based on the narrative
        - false if the goal is not achieved or if there's any ambiguity

        Do NOT include any other text, explanations, or action suggestions in your response.
        """

    def create_system_message(self) -> str:
        # from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
        directory_contents = self.get_directory_contents()
        return f"""
        {self.agent_prompt}
        
        IMPORTANT: After any action that retrieves information or performs a task, you MUST include a send_message_to_student action (for user messages) or other appropriate action.

        Current working directory structure and file contents:
        {directory_contents}
        """
    
    def get_directory_contents(self):
        work_directory = self.agent_config.get('work_directory')
        if not work_directory:
            # If work_directory is not set, use a default directory or return a message
            return "No specific work directory set for this agent."

        # from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
        if not os.path.exists(work_directory):
            return f"Work directory does not exist: {work_directory}"
        structure = []
        for root, dirs, files in os.walk(work_directory):
            level = root.replace(work_directory, '').count(os.sep)
            indent = ' ' * 4 * level
            structure.append(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                if f.endswith(('.py', '.yaml', '.txt', '.md', '.csv')):
                    file_path = os.path.join(root, f)
                    relative_path = os.path.relpath(file_path, work_directory)
                    structure.append(f"{subindent}{relative_path}")
                    with open(file_path, 'r') as file:
                        content = file.read()
                    structure.append(f"{subindent}Content of {relative_path}:")
                    structure.append(f"{subindent}{content}")
        return '\n'.join(structure)


    def get_event_log(self) -> GlobalEventLog:
        return self.global_event_log

    def clear_event_log(self):
        self.arcane_architecture.global_event_log = GlobalEventLog()

    # async def handle_error(self, error: Exception, sender_id: str, communication_channel: CommunicationChannel) -> None:
    #     error_message = f"An error occurred: {str(error)}"
    #     self.logger.error(error_message)
    #     await communication_channel.send_message(error_message)
    #     self.clear_event_log(sender_id)

    async def shutdown(self) -> None:
        self.logger.info("Shutting down ArcaneArchitecture")
        # Add any cleanup code here, such as saving state or closing connections

    async def send_execution_update(self, communication_channel, action_name, brief_result):
        update_message = f"    Executed: {action_name} - {brief_result[:50]}..."
        await communication_channel.send_execution_update(update_message)