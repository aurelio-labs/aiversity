import json
import os
from typing import Dict, Any, Optional, Tuple
from ARCANE.planning.plan_structures import Plan, Level, Task
from ARCANE.actions.action import Action

class CreatePlan(Action):
    def __init__(self, plan_name: str, plan_description: str, llm_response: Dict[str, Any], agent_id: str):
        self.plan_name = plan_name
        self.plan_description = plan_description
        self.llm_response = llm_response
        self.agent_id = agent_id
        self.workspace_root = os.path.join('aiversity_workspaces', agent_id)

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            plan = self._create_plan_from_llm_response()
            return await self._save_plan(plan)
        except Exception as e:
            return False, f"Error creating plan: {str(e)}"

    def _create_plan_from_llm_response(self) -> Plan:
        plan = Plan(self.plan_name, self.plan_description)
        
        for level_data in self.llm_response.get('levels', []):
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

    async def _save_plan(self, plan: Plan) -> Tuple[bool, Optional[str]]:
        plan_dir = os.path.join(self.workspace_root, 'plans')
        os.makedirs(plan_dir, exist_ok=True)
        
        file_path = os.path.join(plan_dir, f"{plan.id}.json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(plan.to_dict(), f, indent=2)
            return True, f"Plan saved successfully: {file_path}"
        except Exception as e:
            return False, f"Error saving plan: {str(e)}"

def load_plan(plan_id: str, agent_id: str) -> Optional[Plan]:
    workspace_root = os.path.join('aiversity_workspaces', agent_id)
    file_path = os.path.join(workspace_root, 'plans', f"{plan_id}.json")
    
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r') as f:
            plan_data = json.load(f)
        
        plan = Plan(plan_data['name'], plan_data['description'])
        plan.id = plan_data['id']
        plan.status = plan_data['status']
        plan.creation_time = datetime.fromisoformat(plan_data['creation_time'])
        plan.last_updated = datetime.fromisoformat(plan_data['last_updated'])
        
        for level_data in plan_data['levels']:
            level = Level(level_data['order'])
            level.id = level_data['id']
            level.status = level_data['status']
            level.start_time = datetime.fromisoformat(level_data['start_time']) if level_data['start_time'] else None
            level.end_time = datetime.fromisoformat(level_data['end_time']) if level_data['end_time'] else None
            
            for task_data in level_data['tasks']:
                task = Task(task_data['name'], task_data['description'], task_data['agent_type'])
                task.id = task_data['id']
                task.status = task_data['status']
                task.start_time = datetime.fromisoformat(task_data['start_time']) if task_data['start_time'] else None
                task.end_time = datetime.fromisoformat(task_data['end_time']) if task_data['end_time'] else None
                level.add_task(task)
            
            plan.add_level(level)
        
        return plan
    except Exception as e:
        print(f"Error loading plan: {str(e)}")
        return None