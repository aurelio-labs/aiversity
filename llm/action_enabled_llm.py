import asyncio
import re
from typing import List, Optional
from ARCANE.actions.action import Action
from ARCANE.actions.generic_agent_actions import (
    SetNextAlarm, UpdateWhiteboard
)
from channels.communication_channel import CommunicationChannel
from llm.LLM import LLMMessage, LLM
from util import parse_json

from ARCANE.actions.file_manipulation import ViewFileContents, EditFileContents, CreateNewFile, RunPythonFile, QueryFileSystem
from ARCANE.actions.triage_agent_actions import SendMessageToStratos, SendMessageToStudent
import json

class ActionEnabledLLM:
    def __init__(self, llm: LLM, model: str, action_layer):
        self.llm = llm
        self.model = model
        self.action_layer = action_layer

        


    async def talk_to_llm_and_execute_actions(self, communication_channel, llm_messages: List[LLMMessage]) -> str:
        try:
            llm_response: LLMMessage = await self.llm.create_conversation_completion(self.model, llm_messages)
            
            if not llm_response or not llm_response.get('content'):
                return "I apologize, but I couldn't generate a response at this time."
            
            response_content = llm_response['content']
            
            try:
                actions = json.loads(response_content)
            except json.JSONDecodeError:
                # If it's not JSON, treat it as a simple message
                return response_content

            response_to_user = ""
            for action in actions:
                if action['action'] == 'send_message_to_student':
                    response_to_user += action['message'] + "\n"
                elif action['action'] == 'update_whiteboard':
                    await self.action_layer.update_whiteboard(action['contents'])
                elif action['action'] == 'wake_again_soon':
                    await self.action_layer.set_next_alarm(action['seconds'])
            
            return response_to_user.strip()
        
        except Exception as e:
            error_message = f"An error occurred while processing your request: {str(e)}"
            print(error_message)
            return error_message

    async def execute_action_and_send_result_to_llm(
            self, action: Action, communication_channel: CommunicationChannel,
            llm_messages: [LLMMessage]):
        print("Executing action: " + str(action))
        action_output: Optional[str] = await action.execute()
        if action_output is None:
            print("No response from action")
            return

        print(f"Got action output:\n{action_output}")

        print("I will add this to the llm conversation and talk to llm again.")

        llm_messages.append({
            "role": "user",
            "name": "action-output",
            "content": action_output
        })

        await self.talk_to_llm_and_execute_actions(communication_channel, llm_messages)

    def parse_actions(self, communication_channel: CommunicationChannel, text: str):
        # Extract JSON content from the text using regex
        json_match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        if not json_match:
            return []
        actions_string = json_match.group(1)

        action_data_list = parse_json(actions_string)

        if action_data_list is None or not isinstance(action_data_list, list):
            return []

        actions = []
        for action_data in action_data_list:
            action = self.parse_action(communication_channel, action_data)
            if action is not None:
                print("Adding action: " + str(action))
                actions.append(action)
            else:
                print("Unknown action: " + str(action_data))
                if communication_channel:
                    actions.append(SendMessageToStudent(
                        communication_channel,
                        f"OK this is embarrassing. "
                        f"My brain asked me to do something that I don't know how to do: {action_data}"
                    ))

        return actions

    def parse_action(self, communication_channel: CommunicationChannel, action_data: dict):
        action_name = action_data.get("action")
        if action_name == "update_whiteboard":
            return UpdateWhiteboard(self.action_layer, action_data["contents"])
        elif action_name == "wake_again_soon":
            return SetNextAlarm(self.action_layer, action_data["seconds"])
        # elif action_name == "speak_text":
        #     return SpeakText(self.action_layer, action_data["text"])
        elif action_name == "view_file_contents":
            return ViewFileContents(action_data["file_path"])
        elif action_name == "edit_file_contents":
            return EditFileContents(action_data["file_path"], action_data["contents"])
        elif action_name == "create_new_file":
            return CreateNewFile(action_data["file_path"])
        elif action_name == "run_python_file":
            return RunPythonFile(action_data["file_path"])
        elif action_name == "send_message_to_student":
            return SendMessageToStudent(communication_channel=communication_channel, message=action_data["message"])
        elif action_name == "send_message_to_stratos":
            return SendMessageToStratos(communication_channel=communication_channel, message=action_data["message"])
        elif action_name == "query_file_system":
            return QueryFileSystem(action_data["command"])
        else:
            print(f"Warning: Unknown action: {action_name}")
            return None
