from ARCANE.actions.action import Action


class SpeakText(Action):
    def __init__(self, action_layer, text: str):
        self.action_layer = action_layer
        self.text = text

    async def execute(self):
        await self.action_layer.speak_text(self.text)

    def __str__(self):
        return f"Speak Text: {self.text}"