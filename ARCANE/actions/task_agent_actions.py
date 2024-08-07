from ARCANE.actions.action import Action
from typing import Tuple, Optional, List, Dict
import aiohttp
import os
import json

class PerplexitySearch(Action):
    def __init__(self, query: str, api_key: str):
        self.query = query
        self.api_key = api_key

    async def execute(self) -> Tuple[bool, Optional[str]]:
        url = "https://api.perplexity.ai/chat/completions"
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "Be precise and concise."
                },
                {
                    "role": "user",
                    "content": self.query
                }
            ]
        }
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.api_key}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    response_data = await response.json()
                    result = response_data["choices"][0]['message']['content']
                    return True, f"Perplexity Search Result:\n{result}"
                else:
                    error_message = await response.text()
                    return False, f"Error performing Perplexity search: {response.status}, {error_message}"

class DeclareComplete(Action):
    def __init__(self, agent_id: str, message: str, files: List[Dict[str, str]], work_directory: str):
        self.agent_id = agent_id
        self.message = message
        self.files = files
        self.work_directory = work_directory

    async def execute(self) -> Tuple[bool, Optional[str]]:
        output = f"TASK_COMPLETE\n{self.message}\n"
        if self.files:
            output += "Files created:\n"
            for file in self.files:
                file_path = os.path.join(self.work_directory, file['name'])
                if os.path.exists(file_path):
                    output += f"File: {file['name']} - {file['description']}\n"
                else:
                    return False, f"Error: File {file['name']} does not exist in the work directory."
        
        return True, output

class CreateFile(Action):
    def __init__(self, file_name: str, content: str, work_directory: str):
        self.file_name = file_name
        self.content = content
        self.work_directory = work_directory

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            file_path = os.path.join(self.work_directory, self.file_name)
            with open(file_path, 'w') as f:
                f.write(self.content)
            return True, f"File {self.file_name} created successfully."
        except Exception as e:
            return False, f"Error creating file {self.file_name}: {str(e)}"

class ReadFile(Action):
    def __init__(self, file_name: str, work_directory: str):
        self.file_name = file_name
        self.work_directory = work_directory

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            file_path = os.path.join(self.work_directory, self.file_name)
            with open(file_path, 'r') as f:
                content = f.read()
            return True, content
        except Exception as e:
            return False, f"Error reading file {self.file_name}: {str(e)}"