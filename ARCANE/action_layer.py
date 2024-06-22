import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler


from llm.action_enabled_llm import ActionEnabledLLM
from ARCANE.types import ChatMessage, Memory, stringify_chat_message, stringify_chat_history, LayerState
from channels.communication_channel import CommunicationChannel
from llm.LLM import LLM
from llm.LLM import LLMMessage
# from memory.weaviate_memory_manager import WeaviateMemoryManager
import requests

import ARCANE.agent_prompting.static.triage_prompts as prompts


chat_history_length_short = 3

chat_history_length = 10

max_memories_to_include = 5


class ActionLayer():
    def __init__(self, name, llm: LLM, model, logger):
        # super().__init__("3")
        self.llm = llm
        self.model = model
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        # self.memory_manager = memory_manager
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

    async def process_incoming_user_message(self, communication_channel: CommunicationChannel):
        await self.set_active(True)
        try:

            # Early out if I don't need to act, for example if I overheard a message that wasn't directed at me
            if not await self.should_act(communication_channel):
                return

            chat_history: [ChatMessage] = await communication_channel.get_message_history(chat_history_length)
            if not chat_history:
                print("Warning: process_incoming_user_message was called with no chat history. That's weird. Ignoring.")
                return
            last_chat_message = chat_history[-1]
            print("\n--------------------------------------------------------")
            # self.logger.info("Got chat message: " + stringify_chat_message(last_chat_message))

            # memories: [Memory] = self.memory_manager.find_relevant_memories(
            #     stringify_chat_message(last_chat_message),
            #     max_memories_to_include
            # )

            # print("Found memories:\n" + json.dumps(memories, indent=2))
            system_message = self.create_system_message()

            memories_if_any = ""
            # if memories:
            #     memories_string = "\n".join(f"- <{memory['time_utc']}>: {memory['content']}" for memory in memories)
            #     memories_if_any = self.prompts.memories.replace("[memories]", memories_string)

            # TODO think about this
            self.preferred_communication_channel = communication_channel

            user_message = (
                self.prompts.act_on_user_input
                .replace("[communication_channel]", communication_channel.describe())
                .replace("[memories_if_any]", memories_if_any)
                .replace("[whiteboard]", self.whiteboard)
                .replace("[chat_history]", stringify_chat_history(chat_history))
            )
            llm_messages: [LLMMessage] = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            # print("System prompt: " + system_message)
            # print("User prompt: " + user_message)
            await self.action_enabled_llm.talk_to_llm_and_execute_actions(communication_channel, llm_messages)
        finally:
            await self.set_active(False)

    async def update_whiteboard(self, contents: str):
        self.logger.info("Updating whiteboard to:\n" + contents)
        self.whiteboard = contents
        # await self.notify_layer_state_subscribers()

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
        # await self.notify_layer_state_subscribers()


    async def speak_text(self, text: str):
        
        try:
            print(text)
            response = requests.post("http://localhost:5050/send-text/", json={"text": "Repeat the following text back to me please, and only the following text: " + text})
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
            print(f"Text sent successfully: {text}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending text: {e}")

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
        """
        return system_message

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
