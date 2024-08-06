# File: ARCANE/planning/plan_executor.py

import asyncio
from typing import Dict, List, Any
from datetime import datetime
from ARCANE.planning.plan_structures import Plan, Level, Task
from ARCANE.planning.plan_persistence import PlanPersistence
from util import get_environment_variable
from llm.LLM import LLM
import logging
import os

MAX_AGENT_ACTIONS = 3

class PlanExecutor:
    def __init__(self, plan: Plan, agent_factory, stratos, llm: LLM, logger: logging.Logger):
        self.plan = plan
        self.agent_factory = agent_factory
        self.stratos = stratos
        self.llm = llm
        self.logger = logger
        self.plan_persistence = PlanPersistence(os.path.join('aiversity_workspaces', stratos.agent_id, 'plans'))

    async def execute_plan(self):
        for level in self.plan.levels:
            level_output = await self.execute_level(level)
            await self.update_plan_status(level)
            await self.plan_persistence.update_plan_status(self.plan)
            
            # Pass level output to the next level
            if level.order < len(self.plan.levels) - 1:
                next_level = self.plan.levels[level.order + 1]
                for task in next_level.tasks:
                    task.description += f"\nContext from previous level: {level_output}"

    async def execute_level(self, level: Level):
        level.status = "In Progress"
        level.start_time = datetime.now()

        tasks = [self.execute_task(task) for task in level.tasks]
        level_results = await asyncio.gather(*tasks)

        level.status = "Completed"
        level.end_time = datetime.now()

        return "\n".join(level_results)

    async def execute_task(self, task: Task):
        task.status = "In Progress"
        task.start_time = datetime.now()
        
        
        self.logger.info(f"Starting execution of task: {task.name}")
        
        task_agent = TaskAgent(task, self.llm, self.logger, MAX_AGENT_ACTIONS, self.agent_factory, self.plan)
        await task_agent.initialize()
        result = await task_agent.execute()
        
        task.status = "Completed"
        task.end_time = datetime.now()
        task.output_message = result
        
        self.logger.info(f"Task completed: {task.name}")
        
        return result

    async def update_plan_status(self, level: Level):
        self.plan.last_updated = datetime.now()
        if all(level.status == "Completed" for level in self.plan.levels):
            self.plan.status = "Completed"
        elif any(level.status == "Failed" for level in self.plan.levels):
            self.plan.status = "Failed"
        else:
            self.plan.status = "In Progress"

class TaskAgent:
    def __init__(self, task: Task, llm: LLM, logger: logging.Logger, max_actions: int, agent_factory, plan: Plan):
        self.task = task
        self.llm = llm
        self.logger = logger
        self.max_actions = max_actions
        self.action_count = 0
        self.narrative = []
        self.agent_factory = agent_factory
        self.plan = plan
        self.arcane_architecture = None

    async def initialize(self):
        task_agent_config = {
            "name": f"Task_{self.task.id}",
            "id": f"task-{self.task.id}",
            "descriptor": f"Task-specific agent for {self.task.name}",
            "allowed_communications": [],
            "specific_context": f"I am a task-specific agent for the task: {self.task.description}",
            "specific_actions": [],
            "personality": "I am focused and efficient in completing my assigned task.",
            "work_directory": self.plan.work_directory, # Use the plan's work directory
            "common_actions": [],
            "port": "n/a"
        }
        self.arcane_architecture = self.agent_factory.create_agent(task_agent_config, task_agent_config['common_actions'], self.llm, self.logger, get_environment_variable('ANT_API_KEY')).arcane_architecture


    async def execute(self):
        try:
            while self.action_count < self.max_actions:
                action = await self.determine_next_action()
                if action["action"] == "declare_complete":
                    return action["params"]["message"]
                
                result = await self.arcane_architecture.execute_action(action, None)
                self.narrative.append(f"Action: {action['action']} - Result: {result}")
                from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
                self.action_count += 1

            return f"MAX_ACTIONS_REACHED: {'; '.join(self.narrative)}"
        except Exception as e:
            self.logger.error(f"Error executing task {self.task.name}: {str(e)}")
            return f"Error: {str(e)}"

    async def determine_next_action(self):
        prompt = f"""
        Task: {self.task.description}
        
        Current progress:
        {'; '.join(self.narrative)}
        
        Determine the next action to take. Available actions:
        - perplexity_search(query)
        - declare_complete(message)
        
        Respond with a JSON object containing the action and its parameters.
        """
        response = await self.llm.create_chat_completion(prompt, "Determine next action", self.llm.get_tool_config("create_action", agent_specific_actions=["perplexity_search", "declare_complete"], isolated_agent=True))
        return response[0]['actions'][0] if response and response[0].get('actions') else None
