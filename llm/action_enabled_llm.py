import asyncio
import re
from typing import Optional

from ARCANE.actions.action import Action
from ARCANE.actions.get_web_content import GetWebContent
from ARCANE.actions.search_web import SearchWeb
from ARCANE.actions.send_message_to_user import SendMessageToUser
from ARCANE.actions.set_next_alarm import SetNextAlarm
from ARCANE.actions.speak_text import SpeakText
from ARCANE.actions.update_whiteboard import UpdateWhiteboard
from channels.communication_channel import CommunicationChannel
from llm.LLM import LLMMessage, LLM
from util import parse_json

from ARCANE.actions.tutoring_actions import ViewFileContents, EditFileContents, CreateNewFile, RunPythonFile



class ActionEnabledLLM:
    def __init__(self, llm: LLM, model: str, action_layer):
        self.llm = llm
        self.model = model
        self.action_layer = action_layer

    async def talk_to_llm_and_execute_actions(
            self, communication_channel: CommunicationChannel, llm_messages: [LLMMessage]):
        llm_response: LLMMessage = await self.llm.create_conversation_completion(self.model, llm_messages)
        llm_response_content = llm_response["content"].strip()
        if llm_response_content:
            llm_messages.append(llm_response)

            print("Raw LLM response:\n" + llm_response_content)

            actions = self.parse_actions(communication_channel, llm_response_content)

            # Start all actions in parallel
            running_actions = []
            for action in actions:
                running_actions.append(
                    self.execute_action_and_send_result_to_llm(
                        action, communication_channel, llm_messages
                    )
                )
            # Wait for all actions to finish
            await asyncio.gather(*running_actions)
        else:
            print("LLM response was empty, so I guess we are done here.")

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
                    actions.append(SendMessageToUser(
                        communication_channel,
                        f"OK this is embarrassing. "
                        f"My brain asked me to do something that I don't know how to do: {action_data}"
                    ))

        return actions

    def parse_action(self, communication_channel: CommunicationChannel, action_data: dict):
        action_name = action_data.get("action")
        if action_name == "get_web_content":
            return GetWebContent(action_data["url"])
        elif action_name == "send_message_to_user":
            return SendMessageToUser(communication_channel, action_data["message"])
        elif action_name == "update_whiteboard":
            return UpdateWhiteboard(self.action_layer, action_data["contents"])
        elif action_name == "wake_again_soon":
            return SetNextAlarm(self.action_layer, action_data["seconds"])
        elif action_name == "speak_text":
            return SpeakText(self.action_layer, action_data["text"])
        elif action_name == "view_file_contents":
            return ViewFileContents(action_data["file_path"])
        elif action_name == "edit_file_contents":
            return EditFileContents(action_data["file_path"], action_data["contents"])
        elif action_name == "create_new_file":
            return CreateNewFile(action_data["file_path"])
        elif action_name == "run_python_file":
            return RunPythonFile(action_data["file_path"])
        elif action_name == "notify_cora":
            return NotifyCora()
        elif action_name == "notify_liam":
            return NotifyLiam()
        elif action_name == "notify_parker":
            return NotifyParker()
        elif action_name == "update_policy_draft":
            return UpdatePolicyDraft(action_data["contents"])
        elif action_name == "update_explanatory_notes":
            return UpdateExplanatoryNotes(action_data["contents"])
        elif action_name == "update_secondary_legislation":
            return UpdateSecondaryLegislation(action_data["contents"])
        elif action_name == "update_bill":
            return UpdateBill(action_data["contents"])
        else:
            print(f"Warning: Unknown action: {action_name}")
            return None
