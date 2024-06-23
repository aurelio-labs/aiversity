import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from llm.action_enabled_llm import ActionEnabledLLM
from ARCANE.types import ChatMessage, stringify_chat_history, LayerState
from channels.communication_channel import CommunicationChannel
from llm.LLM import LLM
from llm.LLM import LLMMessage

import ARCANE.agent_prompting.static.triage_prompts as prompts

class ActionLayer():
    def __init__(self, name, llm: LLM, model, logger):
        self.llm = llm
        self.model = model
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        self.action_enabled_llm = ActionEnabledLLM(llm, model, self)
        self.whiteboard = ""
        self.active: bool = False
        self.next_wakeup_time: Optional[str] = None
        self.preferred_communication_channel = None
        self.name = name
        self.prompts = prompts
        self.logger = logger

    def get_layer_state(self) -> LayerState:
        return {
            "active": self.active,
            "whiteboard": self.whiteboard,
            "next_wakeup_time": self.next_wakeup_time
        }

    async def set_active(self, active: bool):
        self.active = active

    async def process_incoming_user_message(self, communication_channel: CommunicationChannel, chat_history: List[ChatMessage]):
        await self.set_active(True)
        try:
            if not chat_history:
                self.logger.warning("process_incoming_user_message was called with no chat history. Ignoring.")
                return ""

            system_message = self.create_system_message()
            user_message = (
                self.prompts.act_on_user_input
                .replace("[communication_channel]", communication_channel.describe())
                .replace("[whiteboard]", self.whiteboard)
                .replace("[chat_history]", stringify_chat_history(chat_history))
            )
            llm_messages: List[LLMMessage] = [
                {"role": "system", "name": "system", "content": system_message},
                {"role": "user", "name": "user", "content": user_message}
            ]

            response = await self.action_enabled_llm.talk_to_llm_and_execute_actions(communication_channel, llm_messages)
            
            if response is None:
                self.logger.warning("LLM response was None. Returning empty string.")
                return ""
            
            if isinstance(response, dict):
                return response.get('content', '')
            elif isinstance(response, str):
                return response
            else:
                self.logger.warning(f"Unexpected response type: {type(response)}. Returning string representation.")
                return str(response)
        finally:
            await self.set_active(False)

    async def update_whiteboard(self, contents: str):
        self.logger.info("Updating whiteboard to:\n" + contents)
        self.whiteboard = contents

    async def set_next_alarm(self, seconds):
        current_time = datetime.now(timezone.utc)
        next_wakeup_time = current_time + timedelta(seconds=seconds)
        self.next_wakeup_time = next_wakeup_time.isoformat()
        self.logger.info("Setting next wakeup alarm to: " + self.next_wakeup_time)
        self.scheduler.add_job(
            self.on_wakeup_alarm,
            args=(),
            trigger='date',
            next_run_time=next_wakeup_time,
            id="agent-wakeup",
            name="Agent Layer Wakeup Alarm",
            replace_existing=True,
            max_instances=10,
            misfire_grace_time=120
        )

    def create_system_message(self):
        current_time_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        system_message = f"""
                {self.prompts.situational_context}
                {self.prompts.self_identity}
                {self.prompts.personality}
                {self.prompts.knowledge.replace("[current_time_utc]", current_time_utc)}
                {self.prompts.whiteboard}
                {self.prompts.actions}
                {self.prompts.alarm_clock}
                
                Important: Always respond in valid JSON format with an array of action objects. Each action object should have an 'action' field and any necessary additional fields. The possible actions are:
                1. 'send_message_to_student': Include a 'message' field with the text to send to the student.
                2. 'update_whiteboard': Include a 'contents' field with the new whiteboard contents.
                3. 'wake_again_soon': Include a 'seconds' field with the number of seconds to wait before waking up.

                Maintain context throughout the conversation. If asked about previous messages or the user's name, refer to the chat history provided. Do not assume or invent information not present in the chat history.
        """
        return system_message

    async def on_wakeup_alarm(self):
        # print("\n--------------------------------------------------------")
        self.logger.info("Wakeup alarm triggered.")
        await self.set_active(True)
        try:
            system_message = self.create_system_message()
            user_message = (
                self.prompts.act_on_wakeup_alarm
                .replace("[whiteboard]", self.whiteboard)
            )
            llm_messages: [LLMMessage] = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]

            # print("System prompt: " + system_message)
            # print("User prompt: " + user_message)
            await self.action_enabled_llm.talk_to_llm_and_execute_actions(
                self.preferred_communication_channel, llm_messages
            )
            print("Wakeup alarm actions complete. Next wakeup time: " + self.next_wakeup_time)
        finally:
            await self.set_active(False)

    async def should_act(self, communication_channel: CommunicationChannel):
        """
        Ask the LLM whether this is a message that we should act upon.
        This is a cheaper request than asking the LLM to generate a response,
        allows us to early-out for unrelated messages.
        """

        message_history: [ChatMessage] = await communication_channel.get_message_history(
            chat_history_length_short
        )

        prompt = self.prompts.decide_whether_to_respond_prompt.format(
            messages=stringify_chat_history(message_history)
        )

        # print(f"Prompt to determine if we should respond:\n {prompt}")
        # response = await self.llm.create_conversation_completion(
        #     self.model,
        #     [{"role": "user", "name": "user", "content": prompt}]
        # )
        # response_content = response['content'].strip().lower()

        # print(f"Response to prompt: {response_content}")

        # return response_content.startswith("yes")
        return True
