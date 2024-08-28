import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from ARCANE.planning.plan_structures import Plan, Level, Task
from ARCANE.planning.plan_persistence import PlanPersistence
from util import get_environment_variable
from llm.LLM import LLM
import logging
import os
import json

MAX_AGENT_ACTIONS = 5


class PlanExecutor:
    def __init__(
        self, plan: Plan, agent_factory, stratos, llm: LLM, logger: logging.Logger
    ):
        self.plan = plan
        self.agent_factory = agent_factory
        self.stratos = stratos
        self.llm = llm
        self.logger = logger
        self.plan_persistence = PlanPersistence(
            os.path.join("aiversity_workspaces", stratos.agent_id, "plans")
        )

        # Create a plan-specific directory
        self.plan_directory = os.path.join(
            "aiversity_workspaces", stratos.agent_id, "plans", plan.id
        )
        os.makedirs(self.plan_directory, exist_ok=True)
        self.collective_narrative = []

    async def execute_plan(self) -> str:
        collective_narrative = []
        for level in self.plan.levels:
            level_narrative = await self.execute_level(level)
            formatted_level_narrative = self.format_level_narrative(
                level, level_narrative
            )
            collective_narrative.append(formatted_level_narrative)

            # Pass accumulated narrative to the next level
            if level.order < len(self.plan.levels) - 1:
                next_level = self.plan.levels[level.order + 1]
                for task in next_level.tasks:
                    task.description += f"\nContext from previous levels:\n{''.join(collective_narrative)}"

        return "\n".join(collective_narrative)

    def format_level_narrative(self, level: Level, level_narrative: str) -> str:
        return f"=== Level {level.order} ===\n{level_narrative}\n"

    async def execute_level(self, level: Level):
        level.status = "In Progress"
        level.start_time = datetime.now()

        tasks = [self.execute_task(task) for task in level.tasks]
        level_results = await asyncio.gather(*tasks)

        level.status = "Completed"
        level.end_time = datetime.now()

        level_narrative = "\n".join(level_results)
        return level_narrative

    async def execute_task(self, task: Task):
        task.status = "In Progress"
        task.start_time = datetime.now()

        self.logger.info(f"Starting execution of task: {task.name}")

        task_agent = TaskAgent(
            task,
            self.llm,
            self.logger,
            MAX_AGENT_ACTIONS,
            self.agent_factory,
            self.plan,
            self.plan_directory,
            self.get_plan_status(),
        )
        await task_agent.initialize()
        result, task_narrative = await task_agent.execute()

        task.status = "Completed"
        task.end_time = datetime.now()
        task.output_message = result

        self.logger.info(f"Task completed: {task.name}")

        return f"Agent {task.agent_type} - Task: {task.name}\n{task_narrative}"

    def get_plan_status(self) -> str:
        status = []
        for level in self.plan.levels:
            level_status = f"Level {level.order}: {'Completed' if level.status == 'Completed' else 'Pending'}"
            task_statuses = [f"  - {task.name}: {task.status}" for task in level.tasks]
            status.extend([level_status] + task_statuses)
        return "\n".join(status)

    def save_collective_narrative(self):
        narrative_path = os.path.join(self.plan_directory, "collective_narrative.txt")
        with open(narrative_path, "w") as f:
            f.write("\n".join(self.collective_narrative))

    async def update_plan_status(self, level: Level):
        self.plan.last_updated = datetime.now()
        if all(level.status == "Completed" for level in self.plan.levels):
            self.plan.status = "Completed"
        elif any(level.status == "Failed" for level in self.plan.levels):
            self.plan.status = "Failed"
        else:
            self.plan.status = "In Progress"


class TaskAgent:
    def __init__(
        self,
        task: Task,
        llm: LLM,
        logger: logging.Logger,
        max_actions: int,
        agent_factory,
        plan: Plan,
        plan_directory: str,
        plan_status: str,
    ):
        self.task = task
        self.llm = llm
        self.logger = logger
        self.max_actions = max_actions
        self.action_count = 0
        self.narrative = []
        self.agent_factory = agent_factory
        self.plan = plan
        self.plan_directory = plan_directory
        self.arcane_architecture = None
        self.plan_status = plan_status
        self.input_files = task.input_files
        self.output_files = task.output_files
        self.task_agent_config = None

    def summarize_action_result(
        self, action: str, result: str, max_length: int = 200
    ) -> str:
        if len(result) <= max_length or action == "perplexity_search":
            return result
        return f"{result[:max_length]}... [Action result truncated for legibility]"

    async def initialize(self):
        directory_contents = self.get_directory_contents()
        plan_overview = self.get_plan_overview()

        task_agent_config = {
            "name": f"Task_{self.task.id}",
            "id": f"task-{self.task.id}",
            "descriptor": f"Task-specific agent for {self.task.name}",
            "allowed_communications": [],
            "specific_context": f"""I am a task-specific agent for the task: {self.task.description}
            My working directory is: {self.plan_directory}

            Project Directory Structure and File Contents:
            ============
            {directory_contents}
            ============

            Overall Plan Overview:
            {plan_overview}

            Current Plan Status:
            {self.plan_status}

            My role in the plan:
            - I am working on Level {self.task.level.order}
            - My specific task is: {self.task.name}
            - Task description: {self.task.description}
            """,
            "specific_actions": [],
            "personality": "I am focused and efficient in completing my assigned task.",
            "work_directory": self.plan_directory,
            "common_actions": [],
            "port": "n/a",
        }
        self.task_agent_config = task_agent_config
        self.arcane_architecture = self.agent_factory.create_agent(
            task_agent_config,
            task_agent_config["common_actions"],
            self.llm,
            self.logger,
            get_environment_variable("ANT_API_KEY"),
        ).arcane_architecture

    def get_directory_contents(self):
        structure = []
        for root, dirs, files in os.walk(self.plan_directory):
            level = root.replace(self.plan_directory, "").count(os.sep)
            indent = " " * 4 * level
            structure.append(f"{indent}{os.path.basename(root)}/")
            subindent = " " * 4 * (level + 1)
            for f in files:
                if f.endswith((".py", ".yaml", ".txt", ".json", ".md", ".csv")):
                    file_path = os.path.join(root, f)
                    relative_path = os.path.relpath(file_path, self.plan_directory)
                    structure.append(f"{subindent}{relative_path}")
                    with open(file_path, "r") as file:
                        content = file.read()
                    structure.append(f"{subindent}Content of {relative_path}:")
                    structure.append(f"{subindent}{content}")
        return "\n".join(structure)

    def get_plan_overview(self):
        overview = f"Plan: {self.plan.name}\nDescription: {self.plan.description}\n\n"
        for level in self.plan.levels:
            overview += f"Level {level.order}:\n"
            for task in level.tasks:
                overview += (
                    f"  - Task: {task.name}\n    Description: {task.description}\n"
                )
        return overview

    async def execute(self):
        try:
            while self.action_count < self.max_actions:
                action = await self.get_next_action_with_retry()
                
                if action is None:
                    self.logger.error(f"Failed to determine next action for task {self.task.name} after retries")
                    return f"ERROR: Failed to determine next action after retries", "\n".join(self.narrative)

                if action["action"] == "declare_complete":
                    return action["params"]["message"], "\n".join(self.narrative)

                success, result = await self.arcane_architecture.execute_action(action, None)
                summarized_result = self.summarize_action_result(action["action"], str(result))
                self.narrative.append(f"Action: {action['action']} - Result: {summarized_result}")
                self.action_count += 1

            return f"MAX_ACTIONS_REACHED: {'; '.join(self.narrative)}", "\n".join(self.narrative)
        except Exception as e:
            self.logger.error(f"Error executing task {self.task.name}: {str(e)}")
            return f"Error: {str(e)}", f"Error occurred: {str(e)}"

    async def get_next_action_with_retry(self, max_retries: int = 3, initial_delay: float = 2.0) -> Optional[dict]:
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                action_wrapper = await self.determine_next_action()
                
                if action_wrapper and isinstance(action_wrapper, dict):
                    if "action" in action_wrapper and "params" in action_wrapper:
                        return action_wrapper
                    elif "action" in action_wrapper and isinstance(action_wrapper["action"], str):
                        try:
                            return json.loads(action_wrapper["action"])
                        except json.JSONDecodeError:
                            self.logger.error("Failed to parse action JSON")
                
                if attempt < max_retries - 1:
                    self.logger.warning(f"Retrying to determine next action (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
            except Exception as e:
                self.logger.error(f"Error determining next action (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
        
        return None  # If all retries fail

    #         - perplexity_search(query) - should be used for deep-dive research questions on the web. This sends an API request to perplexity and returns a deep-dive. Use sparingly.
    #        - declare_complete(message) - used when your task has been completed.

    async def determine_next_action(self):
        context = self.create_task_context()
        system_message = self.create_system_message()
        action_prompt = self.create_action_prompt(context)
        tool_config = self.llm.get_tool_config(
            "create_action", self.task_agent_config["name"], isolated_agent=True
        )

        full_prompt = f"{system_message}\n\n{action_prompt}"
        # from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
        action_wrapper = await self.llm.create_chat_completion(
            full_prompt, context, tool_config
        )

        return action_wrapper

    def create_system_message(self) -> str:
        base_system_message = self.arcane_architecture.create_system_message()
        task_specific_extension = f"""
        You are currently a task-specific agent working on the following task:
        Task Name: {self.task.name}
        Task Description: {self.task.description}
        
        Your task has the following file inputs and expected outputs:
        Input Files: {', '.join(self.input_files) if self.input_files else 'None'}
        Expected Output Files: {', '.join(self.output_files) if self.output_files else 'None'}
        
        IMPORTANT: You must work only with the specified input and output files. Do not modify or create files that are not in your list of output files. If you need to create intermediate files, use a naming convention that includes your task ID to avoid conflicts.
        
        You are part of a larger plan and should focus on completing your specific task efficiently while adhering to the file management guidelines.
        """
        return f"{base_system_message}\n\n{task_specific_extension}"

    def create_task_context(self):
        return f"""
        Current Progress: {'; '.join(self.narrative)}
        Overall Plan Status: {self.plan_status}
        Current Working Directory: {self.plan_directory}
        Input Files: {', '.join(self.input_files) if self.input_files else 'None'}
        Expected Output Files: {', '.join(self.output_files) if self.output_files else 'None'}
        """

    def create_action_prompt(self, context: str) -> str:
        available_actions = ", ".join(self.get_available_actions())
        return f"""
        CONTEXT:
        {context}

        AVAILABLE ACTIONS:
        {available_actions}

        TASK:
        Based on the context provided and your specific task, determine the most appropriate next action to take. Consider the current progress, overall plan status, available resources, and the specified input and output files.

        IMPORTANT FILE MANAGEMENT GUIDELINES:
        1. Only read from the specified input files.
        2. Only create or modify the specified output files.
        3. If you need to create temporary files, use a naming convention that includes your task ID to avoid conflicts.
        4. Do not attempt to access or modify files that are not in your input or output lists.

        RESPONSE FORMAT:
        Respond with a single action in JSON format, without any additional wrapping:
        {{
            "action": "action_name",
            "params": {{
                "param1": "value1",
                "param2": "value2"
            }}
        }}

        Ensure that you only use actions from the list of available actions provided and include all necessary parameters for the chosen action. Do not include any explanatory text outside of this JSON structure.
        """

    def get_available_actions(self):
        # Based on the actions given ot this agent, we should also fetch their descriptions from some static file.
        # This method should return a list of actions available to this specific task agent
        return [
            "perplexity_search",
            "declare_complete",
            "create_new_file",
            "edit_file_contents",
            "view_file_contents",
        ]
