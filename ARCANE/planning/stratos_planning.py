# File: ARCANE/planning/stratos_planning.py

from typing import Dict, Tuple, Optional, Any
from ARCANE.actions.action import Action
from ARCANE.planning.plan_structures import Plan, Level, Task
from ARCANE.planning.plan_persistence import PlanPersistence
from ARCANE.planning.plan_executor import PlanExecutor
from llm.LLM import LLM
import logging
import os

class CreatePlan(Action):
    def __init__(self, plan_name: str, plan_description: str, agent_id: str, llm: LLM, 
                 agent_factory, stratos, logger: logging.Logger):
        self.plan_name = plan_name
        self.plan_description = plan_description
        self.agent_id = agent_id
        self.llm = llm
        self.agent_factory = agent_factory
        self.stratos = stratos
        self.logger = logger
        self.workspace_root = os.path.join('aiversity_workspaces', agent_id)
        self.plan_persistence = PlanPersistence(os.path.join(self.workspace_root, 'plans'))

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            llm_response = await self._generate_plan_with_llm()
            plan = self._create_plan_from_llm_response(llm_response)
            
            # Create a work directory for the plan
            plan.work_directory = os.path.join(self.workspace_root, 'plans', plan.id)
            os.makedirs(plan.work_directory, exist_ok=True)
            
            await self.plan_persistence.save_plan(plan)
            
            executor = PlanExecutor(plan, self.agent_factory, self.stratos, self.llm, self.logger)
            await executor.execute_plan()
            
            return True, f"Plan created, saved, and executed successfully. Plan ID: {plan.id}"
        except Exception as e:
            return False, f"Error creating or executing plan: {str(e)}"

    async def _generate_plan_with_llm(self) -> Dict[str, Any]:
        tool_config = self.llm.get_tool_config("create_plan")
        prompt = f"""
        I will create a plan for the following task: {self.plan_description}. 
        I will create a structured plan for a complex task, breaking it down into levels and tasks. 
        I shall remember that all tasks on a certain level execute in parallel, i.e. if a task depends on another task, they should be on separate levels. 
        Outputs of previous levels are fed into the next level. By this I mean tasks on one level, don't have observability of outputs from other tasks on the same level. 
        Dependencies should be on different levels. Generate with this flow in mind.
        """
        response = await self.llm.create_chat_completion(prompt, "Generate that plan now. Make sure items on the same level don't depend on each other - context is only passed down after an entire level is completed.", tool_config)
        
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