from ARCANE.actions.action import Action
from channels.communication_channel import CommunicationChannel
import asyncio
import subprocess
from typing import Tuple, Optional
import os

class ViewFileContents(Action):
    def __init__(self, file_path: str, agent_id: str):
        self.file_path = file_path
        self.agent_id = agent_id
        self.workspace_root = os.path.join('aiversity_workspaces', agent_id)

    async def execute(self) -> Tuple[bool, Optional[str]]:
        full_path = os.path.join(self.workspace_root, self.file_path)
        try:
            with open(full_path, 'r') as file:
                content = file.read()
            return True, content
        except FileNotFoundError:
            return False, f"Error: File not found. The file '{self.file_path}' does not exist in the agent's workspace. Please check the file path and try again."
        except PermissionError:
            return False, f"Error: Permission denied. You don't have the necessary permissions to read the file '{self.file_path}'. Please check the file permissions."
        except IsADirectoryError:
            return False, f"Error: '{self.file_path}' is a directory, not a file. Please specify a file path."
        except Exception as e:
            return False, f"Error reading file '{self.file_path}': {str(e)}. This might be due to an I/O error or the file being in use by another process."

    def __str__(self):
        return f"View File Contents: {self.file_path} (Agent: {self.agent_id})"

class EditFileContents(Action):
    def __init__(self, file_path: str, content: str, agent_id: str):
        self.file_path = file_path
        self.content = content
        self.agent_id = agent_id
        self.workspace_root = os.path.join('aiversity_workspaces', agent_id)

    async def execute(self) -> Tuple[bool, Optional[str]]:
        full_path = os.path.join(self.workspace_root, self.file_path)
        try:
            with open(full_path, 'w') as file:
                file.write(self.content)
            return True, f"File edited successfully: {full_path}"
        except FileNotFoundError:
            return False, f"Error: Unable to create or edit file '{self.file_path}'. The directory path does not exist. Please create the necessary directories first."
        except PermissionError:
            return False, f"Error: Permission denied. You don't have the necessary permissions to edit the file '{self.file_path}'. Please check the file and directory permissions."
        except IsADirectoryError:
            return False, f"Error: '{self.file_path}' is a directory, not a file. Please specify a file path for editing."
        except Exception as e:
            return False, f"Error editing file '{self.file_path}': {str(e)}. This might be due to an I/O error, lack of disk space, or the file being in use by another process."

    def __str__(self):
        return f"Edit File Contents: {self.file_path} (Agent: {self.agent_id})"

class CreateNewFile(Action):
    def __init__(self, file_path: str, agent_id: str):
        self.file_path = file_path
        self.agent_id = agent_id
        self.workspace_root = os.path.join('aiversity_workspaces', agent_id)

    async def execute(self) -> Tuple[bool, Optional[str]]:
        full_path = os.path.join(self.workspace_root, self.file_path)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'x') as file:
                pass
            return True, f"File created successfully: {full_path}"
        except FileExistsError:
            return False, f"Error: The file '{self.file_path}' already exists. Use the EditFileContents action to modify an existing file."
        except PermissionError:
            return False, f"Error: Permission denied. You don't have the necessary permissions to create the file '{self.file_path}'. Please check the directory permissions."
        except OSError as e:
            if e.errno == 36:  # File name too long
                return False, f"Error: The file path '{self.file_path}' is too long. Please use a shorter file name or path."
            else:
                return False, f"Error creating file '{self.file_path}': {str(e)}. This might be due to an invalid file name or lack of disk space."
        except Exception as e:
            return False, f"Unexpected error creating file '{self.file_path}': {str(e)}. Please check the file path and try again."

    def __str__(self):
        return f"Create New File: {self.file_path} (Agent: {self.agent_id})"

class RunPythonFile(Action):
    def __init__(self, file_path: str, agent_id: str):
        self.file_path = file_path
        self.agent_id = agent_id
        self.workspace_root = os.path.join('aiversity_workspaces', agent_id)

    async def execute(self) -> Tuple[bool, Optional[str]]:
        full_path = os.path.join(self.workspace_root, self.file_path)
        try:
            if not os.path.exists(full_path):
                return False, f"Error: The file '{self.file_path}' does not exist in the agent's workspace. Please check the file path and try again."
            
            command = f"python {full_path}"
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_root
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = f"File executed successfully: {full_path}\nOutput:\n{stdout.decode()}"
                if stderr:
                    output += f"\nWarnings or non-fatal errors:\n{stderr.decode()}"
                return True, output
            else:
                return False, f"Error executing file '{self.file_path}':\nExit code: {process.returncode}\nError output:\n{stderr.decode()}"
        
        except PermissionError:
            return False, f"Error: Permission denied. You don't have the necessary permissions to execute the file '{self.file_path}'. Please check the file permissions."
        except Exception as e:
            return False, f"Unexpected error running file '{self.file_path}': {str(e)}. This might be due to a syntax error in the Python file or missing dependencies."

    def __str__(self):
        return f"Run Python File: {self.file_path} (Agent: {self.agent_id})"

class QueryFileSystem(Action):
    def __init__(self, command: str, agent_id: str):
        self.command = command
        self.agent_id = agent_id
        self.workspace_root = os.path.join('aiversity_workspaces', agent_id)

    async def execute(self) -> Tuple[bool, Optional[str]]:
        print(f"Executing {self} for agent {self.agent_id}")
        try:
            # Ensure the workspace exists
            os.makedirs(self.workspace_root, exist_ok=True)

            # Construct the full command, constraining it to the agent's workspace
            full_command = f"cd {self.workspace_root} && {self.command}"

            # Execute the command
            result = subprocess.run(full_command, shell=True, check=True, capture_output=True, text=True)
            return True, f"Command executed successfully. Output:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return False, f"Error executing command '{self.command}': {e.output}\nThis might be due to an invalid command or insufficient permissions."
        except FileNotFoundError:
            return False, f"Error: The command '{self.command.split()[0]}' was not found. Please check if the command exists and is correctly spelled."
        except PermissionError:
            return False, f"Error: Permission denied when trying to execute the command '{self.command}'. Please check your permissions in the workspace directory."
        except Exception as e:
            return False, f"Unexpected error querying file system with command '{self.command}': {str(e)}. Please check the command syntax and try again."

    def __str__(self):
        return f"Query File System: {self.command} (Agent: {self.agent_id})"

class UpdateWhiteboard(Action):
    def __init__(self, action_layer, contents: str):
        self.action_layer = action_layer
        self.contents = contents

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            await self.action_layer.update_whiteboard(self.contents)
            return True, "Whiteboard updated successfully"
        except AttributeError:
            return False, "Error: The action layer does not have an 'update_whiteboard' method. Please check the implementation of the action layer."
        except Exception as e:
            return False, f"Error updating whiteboard: {str(e)}. This might be due to network issues or problems with the whiteboard service."

    def __str__(self):
        return "Update whiteboard"