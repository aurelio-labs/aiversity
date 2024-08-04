import json
import os
from typing import Dict, Any, Optional, Tuple
from ARCANE.planning.plan_structures import Plan, Level, Task
from ARCANE.actions.action import Action
import aiofiles
import asyncio

class CreatePlan(Action):
    def __init__(self, plan_name: str, plan_description: str, agent_id: str, llm):
        self.plan_name = plan_name
        self.plan_description = plan_description
        self.agent_id = agent_id
        self.llm = llm
        self.workspace_root = os.path.join('aiversity_workspaces', agent_id)

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            # Generate plan using LLM
            llm_response = await self._generate_plan_with_llm()
            
            # Create plan from LLM response
            plan = self._create_plan_from_llm_response(llm_response)
            
            # Save plan
            success, message = await self._save_plan(plan)
            
            if success:
                return True, f"Plan created and saved successfully: {message}"
            else:
                return False, f"Failed to save plan: {message}"
        except Exception as e:
            return False, f"Error creating plan: {str(e)}"

    async def _generate_plan_with_llm(self) -> Dict[str, Any]:
        tool_config = self.llm.get_tool_config("create_plan")
        prompt = f"Create a plan for the following task: {self.plan_description}"
        response = await self.llm.create_chat_completion(prompt, self.plan_name, tool_config)
        
        if response and isinstance(response, list) and len(response) > 0:
            return response[0].get('plan', {})
        else:
            raise ValueError("Failed to generate plan with LLM")

    def _create_plan_from_llm_response(self, llm_response: Dict[str, Any]) -> Plan:
        plan = Plan(self.plan_name, self.plan_description)
        
        for level_data in llm_response.get('levels', []):
            level = Level(level_data['order'])
            for task_data in level_data.get('tasks', []):
                task = Task(
                    name=task_data['name'],
                    description=task_data['description'],
                    agent_type=task_data['agent_type']
                )
                level.add_task(task)
            plan.add_level(level)
        
        return plan

    async def _save_plan(self, plan: Plan) -> Tuple[bool, str]:
        plan_dir = os.path.join(self.workspace_root, 'plans')
        os.makedirs(plan_dir, exist_ok=True)
        
        file_path = os.path.join(plan_dir, f"{plan.id}.json")
        
        try:
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(plan.to_dict(), indent=2))
            return True, file_path
        except Exception as e:
            return False, f"Error saving plan: {str(e)}"