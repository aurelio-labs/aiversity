import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, TypedDict, Optional, Callable
from anthropic import Anthropic
import openai
import os

from util import get_environment_variable


class LLMMessage(TypedDict):
    role: str
    name: Optional[str]
    content: str


class ChatCompletion(TypedDict):
    model: str
    conversation: List[LLMMessage]


class LLM:
    def __init__(self, provider, api_key):
        self.provider = provider
        self.api_key = api_key
        if provider == "anthropic":
            self.anthropic_api_key = api_key
        else:
            raise EnvironmentError(f"{provider} is not a valid API provider")

        self.executor = ThreadPoolExecutor()
        self.completion_log: List[ChatCompletion] = []
        self.listeners = set()

    def get_completion_log(self) -> List[ChatCompletion]:
        return self.completion_log

    async def create_chat_completion(self, model, system_message, user_message) -> str:
        response = await self.create_conversation_completion(model, [
            {"role": "system", "name": "system", "content": system_message},
            {"role": "user", "name": "user", "content": user_message}
        ])
        return response["content"]

    async def create_conversation_completion(self, model, conversation: List[LLMMessage]) -> LLMMessage:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            self.executor,
            self._create_conversation_completion,
            model, conversation
        )

        # Add the outgoing message and the incoming response to the completion log.
        completion = {
            "model": model,
            "conversation": conversation + [response]
        }
        self.completion_log.append(completion)

        # Notify listeners
        for listener in self.listeners:
            await listener(completion)

        return response

    # def _create_conversation_completion(self, model, conversation: List[LLMMessage]) -> LLMMessage:
    #     print("_create_conversation_completion called for conversation: " + str(conversation))
    #     openai.api_key = self.api_key
    #     chat_completion = openai.ChatCompletion.create(
    #         model=model,
    #         messages=conversation
    #     )
    #     response = chat_completion.choices[0].message
    #     return response


    
    def _create_conversation_completion(self, model, conversation: List[LLMMessage]) -> LLMMessage:
        client = Anthropic(api_key=os.environ.get("ANT_API_KEY"))
        model = get_environment_variable('CLAUDE_DEFAULT_MODEL')
        
        messages = [
            {"role": "assistant" if msg["role"] == "system" else msg["role"], "content": msg["content"]}
            for msg in conversation
        ]

        combined_messages = []
        prev_role = None
        for msg in messages:
            if msg["role"] == prev_role:
                combined_messages[-1]["content"] += "\n" + msg["content"]
            else:
                combined_messages.append(msg)
                prev_role = msg["role"]

        messages = combined_messages

        if messages[0]["role"] != "user":
            messages.insert(0, {"role": "user", "content": "Hello!"})
        
        response = client.messages.create(
            model=model,
            messages=messages,
            max_tokens=4000,
        )
        
        return {
            "role": "assistant",
            "content": response.content[0].text,
        }

    async def create_image(self, prompt, size='256x256') -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._create_image,
            prompt, size
        )

    def _create_image(self, prompt, size='256x256') -> str:
        print("Generating image for prompt: " + prompt)
        openai.api_key = self.api_key
        result = openai.Image.create(
            prompt=prompt,
            n=1,
            size=size
        )
        image_url = result.data[0].url
        print(".... finished generating image for prompt" + prompt + ":\n" + image_url)
        return image_url

    def add_completion_listener(self, listener: Callable[[ChatCompletion], None]) -> None:
        """Add a listener to be notified of completions."""
        self.listeners.add(listener)

    def remove_completion_listener(self, listener: Callable[[ChatCompletion], None]) -> None:
        """Remove a listener."""
        self.listeners.discard(listener)
