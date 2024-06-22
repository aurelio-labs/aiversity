from ARCANE.actions.action import Action


class UpdateWhiteboard(Action):
    def __init__(self, action_layer, contents: str):
        self.action_layer = action_layer
        self.contents = contents

    async def execute(self):
        await self.action_layer.update_whiteboard(self.contents)

    def __str__(self):
        return "Update whiteboard"
