from ARCANE.actions.action import Action
from channels.communication_channel import CommunicationChannel
import asyncio
import subprocess
from typing import Tuple, Optional
import os
import aiohttp

class QueryFileSystem(Action):
    def __init__(self, command: str, work_directory: str):
        self.command = command
        self.work_directory = work_directory

    async def execute(self) -> Tuple[bool, Optional[str]]:
        print(f"Executing {self} in directory {self.work_directory}")
        try:
            # Ensure the workspace exists
            os.makedirs(self.work_directory, exist_ok=True)

            # Construct the full command, constraining it to the work directory
            full_command = f"cd {self.work_directory} && {self.command}"

            # Execute the command
            result = subprocess.run(full_command, shell=True, check=True, capture_output=True, text=True)
            output = result.stdout if result.stdout else "no output returned"
            return True, f"Command '{self.command}' executed successfully. Output:\n{output}"
        except subprocess.CalledProcessError as e:
            return False, f"Error executing command '{self.command}': {e.output}\nThis might be due to an invalid command or insufficient permissions."
        except FileNotFoundError:
            return False, f"Error: The command '{self.command.split()[0]}' was not found. Please check if the command exists and is correctly spelled."
        except PermissionError:
            return False, f"Error: Permission denied when trying to execute the command '{self.command}'. Please check your permissions in the work directory."
        except Exception as e:
            return False, f"Unexpected error querying file system with command '{self.command}': {str(e)}. Please check the command syntax and try again."

    def __str__(self):
        return f"Query File System: {self.command} (Directory: {self.work_directory})"

class ViewFileContents(Action):
    def __init__(self, file_path: str, work_directory: str):
        self.file_path = file_path
        self.work_directory = work_directory

    async def execute(self) -> Tuple[bool, Optional[str]]:
        full_path = os.path.join(self.work_directory, self.file_path)
        try:
            with open(full_path, 'r') as file:
                content = file.read()
            return True, content
        except FileNotFoundError:
            return False, f"Error: File not found. The file '{self.file_path}' does not exist in the work directory. Please check the file path and try again."
        except PermissionError:
            return False, f"Error: Permission denied. You don't have the necessary permissions to read the file '{self.file_path}'. Please check the file permissions."
        except IsADirectoryError:
            return False, f"Error: '{self.file_path}' is a directory, not a file. Please specify a file path."
        except Exception as e:
            return False, f"Error reading file '{self.file_path}': {str(e)}. This might be due to an I/O error or the file being in use by another process."

class EditFileContents(Action):
    def __init__(self, file_path: str, content: str, work_directory: str):
        self.file_path = file_path
        self.content = content
        self.work_directory = work_directory

    async def execute(self) -> Tuple[bool, Optional[str]]:
        full_path = os.path.join(self.work_directory, self.file_path)
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

class CreateNewFile(Action):
    def __init__(self, file_path: str, work_directory: str):
        self.file_path = file_path
        self.work_directory = work_directory

    async def execute(self) -> Tuple[bool, Optional[str]]:
        full_path = os.path.join(self.work_directory, self.file_path)
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

class RunPythonFile(Action):
    def __init__(self, file_path: str, work_directory: str):
        self.file_path = file_path
        self.work_directory = work_directory

    async def execute(self) -> Tuple[bool, Optional[str]]:
        full_path = os.path.join(self.work_directory, self.file_path)
        try:
            if not os.path.exists(full_path):
                return False, f"Error: The file '{self.file_path}' does not exist in the work directory. Please check the file path and try again."
            
            command = f"python {full_path}"
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.work_directory
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
    

class SendNIACLMessage(Action):
    def __init__(self, receiver: str, message: str, sender: str, agent_config: dict):
        self.receiver = receiver
        self.message = message
        self.sender = sender
        self.agent_config = agent_config

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            receiver_port = self.get_agent_port(self.receiver)
            if not receiver_port:
                return False, f"Unable to find port for agent {self.receiver}"

            url = f"http://localhost:{receiver_port}/agent-message/"
            
            # Create a new event loop for the asynchronous HTTP request
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def send_request():
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json={"message": self.message, "sender": self.sender}) as response:
                        await response.text()  # We don't wait for the response content

            # Run the request in the background
            asyncio.create_task(send_request())
            
            return True, f"Message sent asynchronously to {self.receiver}. Don't wait for a response, the agent is processing this."
        except Exception as e:
            print(str(e))
            return False, f"Error sending NIACL message: {str(e)}"

    def get_agent_port(self, agent_id: str) -> Optional[int]:
        # Extract the port from the agent ID
        # Assuming the format is always NAME-PORT
        try:
            return int(agent_id.split('-')[-1])
        except ValueError:
            return None