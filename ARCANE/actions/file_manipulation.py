from ARCANE.actions.action import Action
from channels.communication_channel import CommunicationChannel
import asyncio
import subprocess
from typing import Tuple, Optional

class ViewFileContents(Action):
    def __init__(self, file_path: str):
        self.file_path = file_path

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            with open(self.file_path, 'r') as file:
                content = file.read()
            return True, content
        except FileNotFoundError:
            return False, f"File not found: {self.file_path}"
        except Exception as e:
            return False, f"Error reading file: {self.file_path}\n{str(e)}"

    def __str__(self):
        return f"View File Contents: {self.file_path}"

class EditFileContents(Action):
    def __init__(self, file_path: str, content: str):
        self.file_path = file_path
        self.content = content

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            with open(self.file_path, 'w') as file:
                file.write(self.content)
            return True, f"File edited successfully: {self.file_path}"
        except Exception as e:
            return False, f"Error editing file: {self.file_path}\n{str(e)}"

    def __str__(self):
        return f"Edit File Contents: {self.file_path}"

class CreateNewFile(Action):
    def __init__(self, file_path: str):
        self.file_path = file_path

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            with open(self.file_path, 'w') as file:
                pass
            return True, f"File created successfully: {self.file_path}"
        except Exception as e:
            return False, f"Error creating file: {self.file_path}\n{str(e)}"

    def __str__(self):
        return f"Create New File: {self.file_path}"

class RunPythonFile(Action):
    def __init__(self, file_path: str):
        self.file_path = file_path

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            command = f"python {self.file_path}"
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            output = f"File executed: {self.file_path}\nOutput:\n{stdout.decode()}\nErrors:\n{stderr.decode()}"
            return True, output
        except Exception as e:
            return False, f"Error running file: {self.file_path}\n{str(e)}"

    def __str__(self):
        return f"Run Python File: {self.file_path}"
   
class QueryFileSystem(Action):
    def __init__(self, command: str):
        self.command = command

    async def execute(self) -> Tuple[bool, Optional[str]]:
        print("Executing " + str(self))
        try:
            # Here we use subprocess to execute the command
            # Be cautious with this approach as it can be a security risk if not properly sanitized
            result = subprocess.run(self.command, shell=True, check=True, capture_output=True, text=True)
            return True, f"Command executed successfully. Output:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return False, f"Error executing command: {e.output}"
        except Exception as e:
            return False, f"Error querying file system: {str(e)}"

    def __str__(self):
        return f"Query File System: {self.command}"

class UpdateWhiteboard(Action):
    def __init__(self, action_layer, contents: str):
        self.action_layer = action_layer
        self.contents = contents

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            await self.action_layer.update_whiteboard(self.contents)
            return True, "Whiteboard updated successfully"
        except Exception as e:
            return False, f"Error updating whiteboard: {str(e)}"

    def __str__(self):
        return "Update whiteboard"