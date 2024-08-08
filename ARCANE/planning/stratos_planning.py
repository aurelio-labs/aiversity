# File: ARCANE/planning/stratos_planning.py

from typing import Dict, Tuple, Optional, Any
from ARCANE.actions.action import Action
from ARCANE.planning.plan_structures import Plan, Level, Task
from ARCANE.planning.plan_persistence import PlanPersistence
from ARCANE.planning.plan_executor import PlanExecutor
from llm.LLM import LLM
import logging
import os

class DelegateAndExecuteTask(Action):
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
            
            plan.work_directory = os.path.join(self.workspace_root, 'plans', plan.id)
            os.makedirs(plan.work_directory, exist_ok=True)
            
            await self.plan_persistence.save_plan(plan)
            
            executor = PlanExecutor(plan, self.agent_factory, self.stratos, self.llm, self.logger)
            collective_narrative = await executor.execute_plan()
            
            # Generate a detailed summary message
            summary_message = (f"Task '{plan.name}' was delegated and executed successfully. "
                               f"Description: {plan.description}\n\n"
                               f"Execution Details:\n{collective_narrative}\n\n"
                               f"This task was broken down into subtasks and executed by specialized agents.")
            
            return True, summary_message
        except Exception as e:
            return False, f"Error delegating and executing task: {str(e)}"

    async def _generate_plan_with_llm(self) -> Dict[str, Any]:
        tool_config = self.llm.get_tool_config("delegate_and_execute_task")
        prompt = f"""
        I will create a plan for the following task: {self.plan_description}. 
        I will create a structured plan for a complex task, breaking it down into levels and tasks. 
        I shall remember that all tasks on a certain level execute in parallel, i.e. if a task depends on another task, they should be on separate levels. 
        Outputs of previous levels are fed into the next level. By this I mean tasks on one level, don't have observability of outputs from other tasks on the same level. 
        Dependencies should be on different levels. Generate with this flow in mind.
        
        IMPORTANT: When I use the delegate_and_execute_task action, I create a plan, delegate subtasks to specialized agents, and execute the entire task in a single step. The task will be fully planned, delegated, and executed before the action completes. The result of delegate_and_execute_task will provide a detailed summary of the task execution, including the actions taken by other agents.

        Example of delegate_and_execute_task action:
        {{
        "action": "delegate_and_execute_task",
        "params": {{
            "task_name": "Create Study Schedule",
            "task_description": "Create a comprehensive study schedule for a university student"
        }}
        }}

        After using delegate_and_execute_task, I should evaluate whether the goal has been achieved based on the detailed execution summary provided in the result.
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
                    agent_type=task_data['agent_type'],
                    level=level  # Pass the parent level
                )
                level.add_task(task)
            plan.add_level(level)
        
        return plan