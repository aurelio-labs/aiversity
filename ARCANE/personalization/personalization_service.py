import os
import asyncio
from typing import Dict, Any
from llm.LLM import LLM
from util import get_environment_variable
import aiofiles

class PersonalizationService:
    def __init__(self, llm: LLM, logger):
        self.llm = llm
        self.logger = logger
        self.whiteboard_path = os.path.join("aiversity_workspaces", "iris-5000", "personalization_whiteboard.txt")
        self.update_frequency = int(get_environment_variable("PERSONALIZATION_FREQ"))
        self.interaction_count = 0

    async def update_whiteboard(self, user_id: str, message_content: str):
        self.interaction_count += 1
        if self.interaction_count % self.update_frequency == 0:
            await self._perform_update(user_id, message_content)

    async def _perform_update(self, user_id: str, message_content: str):
        current_whiteboard = await self._read_whiteboard()
        update_prompt = self._create_update_prompt(current_whiteboard, user_id, message_content)
        
        updated_whiteboard = await self.llm.create_chat_completion(
            update_prompt,
            "Update the personalization whiteboard based on the new interaction, focusing only on educationally relevant information."
        )

        if updated_whiteboard:
            await self._write_whiteboard(updated_whiteboard)
        else:
            self.logger.warning("Failed to update personalization whiteboard")

    async def _read_whiteboard(self) -> str:
        if not os.path.exists(self.whiteboard_path):
            return "PERSONALIZATION_INFORMATION"
        
        async with aiofiles.open(self.whiteboard_path, 'r') as f:
            return await f.read()

    async def _write_whiteboard(self, content: str):
        async with aiofiles.open(self.whiteboard_path, 'w') as f:
            await f.write(content)

    def _create_update_prompt(self, current_whiteboard: str, user_id: str, message_content: str) -> str:
        return f"""
        You are an educational personalization assistant. Your task is to maintain and update a concise whiteboard of educationally relevant information about the user. Focus only on information that is directly applicable to tailoring their learning experience.

        Current Whiteboard:
        {current_whiteboard}

        User ID: {user_id}
        New Message: {message_content}

        Guidelines:
        1. Only add or modify information if it's significantly relevant to the user's educational needs or preferences.
        2. Do not feel obligated to add information after every interaction. Only update when truly necessary.
        3. Keep the whiteboard concise and focused. Remove any irrelevant or outdated information.
        4. If no update is needed, simply return the current whiteboard content unchanged.

        Please provide a complete rewrite of the entire whiteboard, incorporating any new, educationally relevant information if necessary. If no update is needed, return the current content as is.
        """

    async def personalize_file(self, file_path: str, file_content: str) -> str:
        whiteboard_content = await self._read_whiteboard()
        personalization_prompt = self._create_personalization_prompt(whiteboard_content, file_content)

        personalized_content = await self.llm.create_chat_completion(
            personalization_prompt,
            "Personalize the file content based on the user's educational information."
        )

        if personalized_content:
            return personalized_content
        else:
            self.logger.warning(f"Failed to personalize file: {file_path}")
            return file_content

    def _create_personalization_prompt(self, whiteboard_content: str, file_content: str) -> str:
        return f"""
        You are an educational personalization assistant. Your task is to personalize the given file content
        based on the user's educational information stored in the personalization whiteboard.
        Modify the content to better suit the user's learning preferences, knowledge level, and educational needs.

        Personalization Whiteboard:
        {whiteboard_content}

        Original File Content:
        {file_content}

        Guidelines:
        1. Only make changes that are educationally relevant and beneficial to the user's learning experience.
        2. If no personalization is needed, return the original content unchanged.
        3. Focus on adapting the content to the user's known learning style, knowledge level, and educational goals.
        4. Ensure that any modifications maintain the educational integrity of the original content.
        5. Do NOT include any explanations or justifications for the changes made.
        6. Return ONLY the personalized content, without any additional text or commentary.

        Please provide the personalized version of the file content, taking into account the user's educational information. If no personalization is necessary, return the original content as is.
        """