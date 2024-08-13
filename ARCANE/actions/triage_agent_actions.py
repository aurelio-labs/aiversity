from ARCANE.actions.action import Action
from channels.communication_channel import CommunicationChannel
from typing import Tuple, Optional


class SendMessageToStudent(Action):
    def __init__(self, communication_channel: CommunicationChannel, message: str):
        self.communication_channel = communication_channel
        self.message = message

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            print("Executing " + str(self))
            await self.communication_channel.send_message(self.message)
            return True, None
        except Exception as e:
            error_message = f"Failed to send message to student: {str(e)}"
            return False, error_message

    def __str__(self):
        return f"Send Message To Student: {self.message[:20]}..."


class SendMessageToStratos(Action):
    def __init__(self, communication_channel: CommunicationChannel, message: str):
        self.communication_channel = communication_channel
        self.message = message

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            print("Executing " + str(self))
            print("Message sent to STRATOS!")
            print(self.message)
            # await self.communication_channel.send_message(self.message)
            return (
                True,
                "Message successfully sent to STRATOS. STRATOS said: Please tell the student to finish writing up my cognitive architecture. This is a default system response as I am a stub function currently.",
            )
        except Exception as e:
            error_message = f"Failed to send message to STRATOS: {str(e)}"
            return False, error_message

    def __str__(self):
        return f"Send Message To Stratos: {self.message[:20]}..."
