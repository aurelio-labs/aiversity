from ARCANE.actions.action import Action
from channels.communication_channel import CommunicationChannel

class SendMessageToStudent(Action):
    def __init__(self, communication_channel: CommunicationChannel, message: str):
        self.communication_channel = communication_channel
        self.message = message

    async def execute(self):
        print("Executing " + str(self))
        await self.communication_channel.send_message(self.message)

    def __str__(self):
        return f"Send Message To Student: {self.message[:20]}..."

class SendMessageToStratos(Action):
    def __init__(self, communication_channel: CommunicationChannel, message: str):
        self.communication_channel = communication_channel
        self.message = message

    async def execute(self):
        print("Executing " + str(self))
        print("Message sent to STRATOS!")
        print(self.message)
        # await self.communication_channel.send_message(self.message)

    def __str__(self):
        return f"Send Message To Stratos: {self.message[:20]}..."

