from ARCANE.actions.action import Action


class SetNextAlarm(Action):
    def __init__(self, action_layer, seconds):
        self.action_layer = action_layer
        self.seconds = seconds

    async def execute(self):
        await self.action_layer.set_next_alarm(self.seconds)

    def __str__(self):
        return "Update whiteboard"
