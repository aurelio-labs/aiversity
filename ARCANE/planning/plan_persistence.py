import json
import os
import aiofiles
from ARCANE.planning.plan_structures import Plan

class PlanPersistence:
    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    async def save_plan(self, plan: Plan):
        file_path = os.path.join(self.base_path, f"{plan.id}.json")
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(json.dumps(plan.to_dict(), indent=2))

    async def load_plan(self, plan_id: str) -> Plan:
        file_path = os.path.join(self.base_path, f"{plan_id}.json")
        async with aiofiles.open(file_path, 'r') as f:
            plan_data = json.loads(await f.read())
        return Plan.from_dict(plan_data)

    async def update_plan_status(self, plan: Plan):
        await self.save_plan(plan)