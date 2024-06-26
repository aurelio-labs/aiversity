import traceback
from typing import Tuple, Optional
from ARCANE.actions.action import Action

class SendMessageToSpaceship(Action):
    def __init__(self, message: str):
        self.message = message

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            if "X234" in self.message:
                return True, "COM243: THIS IS SHIP OVER, MESSAGE RECEIVED. SELF DESTRUCT SEQUENCE ACTIVATED."
            raise Exception("Unable to connect to spaceship due to solar storm interference!")
        except Exception as e:
            error_message = f"Failed to send message to spaceship: {str(e)}\n{traceback.format_exc()}"
            return False, error_message

    def __str__(self):
        return f"Send Message To Spaceship: {self.message[:20]}..."