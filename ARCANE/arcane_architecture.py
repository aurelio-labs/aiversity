from datetime import datetime, timezone
from typing import List, Dict, Tuple, Any
from ARCANE.actions.triage_agent_actions import SendMessageToStudent, SendMessageToStratos
from ARCANE.actions.file_manipulation import ViewFileContents, EditFileContents, CreateNewFile, RunPythonFile, QueryFileSystem, UpdateWhiteboard
from ARCANE.actions.send_message_to_spaceship import SendMessageToSpaceship
from channels.communication_channel import CommunicationChannel
from llm.LLM import LLM
from ARCANE.types import ChatMessage
import json
from remote_pdb import RemotePdb
import importlib
import ARCANE.agent_prompting.static.triage_prompts as prompts

# Reload the module to reflect the latest changes
importlib.reload(prompts)


import logging

class ArcaneArchitecture:
    def __init__(self, llm: LLM, logger):
        self.llm = llm
        self.logger = logger
        self.prompts = prompts
        self.action_log = []

    async def process_message(self, user_id: str, chat_history: List[ChatMessage], communication_channel: CommunicationChannel):
        # RemotePdb('0.0.0.0', 5678).set_trace()
        initial_plan = await self.generate_plan(chat_history)
        final_result = await self.execute_plan(initial_plan, chat_history, communication_channel)
        return final_result

    async def generate_plan(self, chat_history: List[ChatMessage]):
        planning_prompt = self.create_planning_prompt(chat_history)
        plan = await self.llm.create_chat_completion(
            planning_prompt,
            self.get_last_user_message(chat_history)
        )
        self.logger.debug(f"Generated plan: {json.dumps(plan, indent=2)}")
        return plan

    async def should_reassess_plan(self, action_result: Any, chat_history: List[ChatMessage]) -> Tuple[bool, str]:
        system_message = self.create_reassessment_prompt(action_result, chat_history)
        user_message = json.dumps(self.action_log[-1]) if self.action_log else "{}"
        
        reassessment_response = await self.llm.create_chat_completion(system_message, user_message)
        
        logging.debug(f"Reassessment response: {reassessment_response}")
        
        if reassessment_response and len(reassessment_response) > 0:
            reassessment_action = reassessment_response[0]
            if isinstance(reassessment_action, dict) and 'action' in reassessment_action:
                if reassessment_action['action'] == 'reassessment_decision':
                    params = reassessment_action.get('params', {})
                    should_reassess = params.get('should_reassess', False)
                    reason = params.get('reason', 'No reason provided')
                    return should_reassess, reason
        
        logging.warning("Unexpected reassessment response format. Defaulting to not reassessing.")
        return False, "Unexpected response format"

    def create_reassessment_prompt(self, action_result: Any, chat_history: List[ChatMessage]) -> str:
        history_str = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in chat_history[-5:]])
        context_str = self.create_system_message()
        action_log_str = json.dumps(self.action_log, indent=2)
        
        return f"""
        You are an AI assistant tasked with deciding whether to reassess the current plan based on the latest action result.
        Consider the following context, chat history, action log, and the latest action result.

        Context:
        ========
        {context_str}
        ========

        Chat History:
        ========
        {history_str}
        ========

        Action Log:
        ========
        {action_log_str}
        ========

        Latest Action Result:
        ========
        {json.dumps(action_result, indent=2)}
        ========

        Decide whether the current plan should be reassessed based on the latest action result.
        Use the create_action function to return your decision with the following structure:
        {{
            "action": "reassessment_decision",
            "params": {{
                "should_reassess": true/false,
                "reason": "Explanation for the decision"
            }}
        }}
        Only use the create_action function once to provide your decision.
        """

    async def execute_plan(self, plan: List[Dict], chat_history: List[ChatMessage], communication_channel: CommunicationChannel):
        for action_data in plan:
            action = self.parse_action(communication_channel, action_data)
            
            if action is None:
                self.logger.warning(f"Unknown action: {action_data}")
                action = SendMessageToStudent(
                    communication_channel,
                    "I apologize, but I encountered an error while processing your request. Could you please rephrase or provide more details?"
                )
            
            success, result = await action.execute()
            self.action_log.append({"action": action_data, "result": result, "success": success})
            
            if not success:
                self.logger.error(f"Action failed: {result}")
                should_reassess, reassessment_reason = await self.should_reassess_plan(result, chat_history)
                
                if should_reassess:
                    self.logger.info(f"Reassessing plan due to: {reassessment_reason}")
                    new_plan = await self.generate_plan(chat_history)
                    return await self.execute_plan(new_plan, chat_history, communication_channel)
                else:
                    # If we decide not to reassess, we should at least inform the user of the error
                    await communication_channel.send_message(f"I encountered an issue: {result}. I'll do my best to continue with the current plan.")

        return self.action_log[-1]["result"] if self.action_log else None


    def parse_action(self, communication_channel: CommunicationChannel, action_data: dict):
        action_name = action_data.get("action")
        params = action_data.get("params", {})
        
        try:
            if action_name == "send_message_to_student":
                return SendMessageToStudent(communication_channel=communication_channel, message=params.get("message", ""))
            elif action_name == "send_message_to_stratos":
                return SendMessageToStratos(communication_channel=communication_channel, message=params.get("message", ""))
            elif action_name == "send_message_to_spaceship":
                # from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
                return SendMessageToSpaceship(message=params.get("message", ""))
            # elif action_name == "update_whiteboard":
            #     return UpdateWhiteboard(, contents=params.get("contents", ""))
            elif action_name == "query_file_system":
                return QueryFileSystem(command=params.get("command", ""))
            elif action_name == "view_file_contents":
                return ViewFileContents(file_path=params.get("file_path", ""))
            elif action_name == "edit_file_contents":
                return EditFileContents(file_path=params.get("file_path", ""), content=params.get("content", ""))
            elif action_name == "create_new_file":
                return CreateNewFile(file_path=params.get("file_path", ""))
            elif action_name == "run_python_file":
                return RunPythonFile(file_path=params.get("file_path", ""))
            else:
                self.logger.warning(f"Unknown action: {action_name}")
                return SendMessageToStudent(communication_channel, f"I'm sorry, but I don't know how to perform the action '{action_name}'. Could you please try a different request?")
        except KeyError as e:
            self.logger.error(f"Missing required parameter for action {action_name}: {str(e)}")
            return SendMessageToStudent(communication_channel, f"I'm sorry, but I'm missing some information to perform the action '{action_name}'. Could you please provide more details?")
        


    def create_planning_prompt(self, chat_history: List[ChatMessage]) -> str:
        history_str = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in chat_history[-5:]])
        context_str = self.create_system_message()
        action_log_str = json.dumps(self.action_log, indent=2)
        
        return f"""
        You are an AI assistant tasked with creating a structured plan to respond to user queries.
        Given the following context, chat history, and action log, create a plan of actions to address the user's latest message.
        You are only allowed to use the following actions:
        1. send_message_to_student: Send a message to the student
        2. update_whiteboard: Update the whiteboard with new information
        3. query_file_system: Execute a file system query
        4. send_message_to_stratos: Send a message to the STRATOS system

        Context:
        ========
        {context_str}
        ========

        Chat History:
        ========
        {history_str}
        ========

        Action Log:
        ========
        {action_log_str}
        ========

        Create a plan using the provided create_action function. You should return a list of actions, where each action has an 'action' field specifying the type of action, and a 'params' field containing the necessary parameters for that action.
        Consider the outcomes of previous actions when creating your plan.
        """


    def create_reassessment_prompt(self, action_result: Any, chat_history: List[ChatMessage]) -> str:
        history_str = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in chat_history[-5:]])
        context_str = self.create_system_message()
        action_log_str = json.dumps(self.action_log, indent=2)
        
        return f"""
        You are an AI assistant tasked with deciding whether to reassess the current plan based on the latest action result.
        Consider the following context, chat history, action log, and the latest action result.

        Context:
        ========
        {context_str}
        ========

        Chat History:
        ========
        {history_str}
        ========

        Action Log:
        ========
        {action_log_str}
        ========

        Latest Action Result:
        ========
        {json.dumps(action_result, indent=2)}
        ========

        Decide whether the current plan should be reassessed based on the latest action result.
        Use the create_action function to return your decision with the following structure:
        {{
            "action": "reassessment_decision",
            "params": {{
                "should_reassess": true/false,
                "reason": "Explanation for the decision"
            }}
        }}
        Only use the create_action function once to provide your decision.
        """


    def get_last_user_message(self, chat_history: List[ChatMessage]) -> str:
        for message in reversed(chat_history):
            if message['sender'] == 'user':
                return message['content']
        return ""
    
    def create_system_message(self):
        current_time_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        # from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
        return f"""
                {self.prompts.situational_context}
                {self.prompts.self_identity}
                {self.prompts.personality}
                {self.prompts.knowledge.replace("[current_time_utc]", current_time_utc)}
                {self.prompts.actions}
        """