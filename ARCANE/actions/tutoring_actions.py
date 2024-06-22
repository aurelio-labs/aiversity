from ARCANE.actions.action import Action
import asyncio
import os

class ViewFileContents(Action):
    def __init__(self, file_path: str):
        self.file_path = file_path

    async def execute(self):
        try:
            with open(self.file_path, 'r') as file:
                content = file.read()
            return content
        except FileNotFoundError:
            return f"File not found: {self.file_path}"

    def __str__(self):
        return f"View File Contents: {self.file_path}"

class EditFileContents(Action):
    def __init__(self, file_path: str, content: str):
        self.file_path = file_path
        self.content = content

    async def execute(self):
        try:
            with open(self.file_path, 'w') as file:
                file.write(self.content)
            return f"File edited successfully: {self.file_path}"
        except Exception as e:
            return f"Error editing file: {self.file_path}\n{str(e)}"

    def __str__(self):
        return f"Edit File Contents: {self.file_path}"

class CreateNewFile(Action):
    def __init__(self, file_path: str):
        self.file_path = file_path

    async def execute(self):
        try:
            with open(self.file_path, 'w') as file:
                pass
            return f"File created successfully: {self.file_path}"
        except Exception as e:
            return f"Error creating file: {self.file_path}\n{str(e)}"

    def __str__(self):
        return f"Create New File: {self.file_path}"

class RunPythonFile(Action):
    def __init__(self, file_path: str):
        self.file_path = file_path

    async def execute(self):
        try:
            command = f"python {self.file_path}"
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return f"File executed: {self.file_path}\nOutput:\n{stdout.decode()}\nErrors:\n{stderr.decode()}"
        except Exception as e:
            return f"Error running file: {self.file_path}\n{str(e)}"

    def __str__(self):
        return f"Run Python File: {self.file_path}"
    
class NotifyCora(Action):
    async def execute(self):
        try:
            with open("wake_cora.txt", "w") as file:
                file.write("1")
            return "Notified Cora successfully"
        except Exception as e:
            return f"Error notifying Cora: {str(e)}"

    def __str__(self):
        return "Notify Cora"

class NotifyLiam(Action):
    async def execute(self):
        try:
            with open("wake_liam.txt", "w") as file:
                file.write("1")
            return "Notified Liam successfully"
        except Exception as e:
            return f"Error notifying Liam: {str(e)}"

    def __str__(self):
        return "Notify Liam"

class NotifyParker(Action):
    async def execute(self):
        try:
            with open("wake_parker.txt", "w") as file:
                file.write("1")
            return "Notified Parker successfully"
        except Exception as e:
            return f"Error notifying Parker: {str(e)}"

    def __str__(self):
        return "Notify Parker"
    

class UpdatePolicyDraft(Action):
    def __init__(self, contents: str):
        self.contents = contents

    async def execute(self):
        try:
            with open("policy_draft.txt", "w") as file:
                file.write(self.contents)
            return "Policy draft updated successfully"
        except Exception as e:
            return f"Error updating policy draft: {str(e)}"

    def __str__(self):
        return "Update policy draft"

class UpdateExplanatoryNotes(Action):
    def __init__(self, contents: str):
        self.contents = contents

    async def execute(self):
        try:
            with open("explanatory_notes.txt", "w") as file:
                file.write(self.contents)
            return "Explanatory notes draft updated successfully"
        except Exception as e:
            return f"Error updating explanatory notes draft: {str(e)}"

    def __str__(self):
        return "Update explanatory notes draft"
    
class UpdateSecondaryLegislation(Action):
    def __init__(self, contents: str):
        self.contents = contents

    async def execute(self):
        try:
            with open("secondary_legislation.txt", "w") as file:
                file.write(self.contents)
            return "Secondary legislation draft updated successfully"
        except Exception as e:
            return f"Error updating secondary legislation draft: {str(e)}"

    def __str__(self):
        return "Update secondary legislation draft"

class UpdateBill(Action):
    def __init__(self, contents: str):
        self.contents = contents

    async def execute(self):
        try:
            with open("bill.txt", "w") as file:
                file.write(self.contents)
            return "Bill updated successfully"
        except Exception as e:
            return f"Error updating Bill: {str(e)}"

    def __str__(self):
        return "Update Bill"

