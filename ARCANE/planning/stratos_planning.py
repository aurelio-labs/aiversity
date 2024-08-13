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
    def __init__(
        self,
        plan_name: str,
        plan_description: str,
        agent_id: str,
        llm: LLM,
        agent_factory,
        stratos,
        logger: logging.Logger,
    ):
        self.plan_name = plan_name
        self.plan_description = plan_description
        self.agent_id = agent_id
        self.llm = llm
        self.agent_factory = agent_factory
        self.stratos = stratos
        self.logger = logger
        self.workspace_root = os.path.join("aiversity_workspaces", agent_id)
        self.plan_persistence = PlanPersistence(
            os.path.join(self.workspace_root, "plans")
        )

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            # from remote_pdb import RemotePdb; RemotePdb('0.0.0.0', 5678).set_trace()
            llm_response = await self._generate_plan_with_llm()
            plan = self._create_plan_from_llm_response(llm_response)

            plan.work_directory = os.path.join(self.workspace_root, "plans", plan.id)
            os.makedirs(plan.work_directory, exist_ok=True)

            await self.plan_persistence.save_plan(plan)

            executor = PlanExecutor(
                plan, self.agent_factory, self.stratos, self.llm, self.logger
            )
            collective_narrative = await executor.execute_plan()

            # Generate a detailed summary message
            summary_message = (
                f"Task '{plan.name}' was delegated and executed successfully. "
                f"Description: {plan.description}\n\n"
                f"Execution Details:\n{collective_narrative}\n\n"
                f"This task was broken down into subtasks and executed by specialized agents."
            )

            return True, summary_message
        except Exception as e:
            return False, f"Error delegating and executing task: {str(e)}"

    async def _generate_plan_with_llm(self) -> Dict[str, Any]:

        tool_config = self.llm.get_tool_config(
            "delegate_and_execute_task", self.agent_id
        )
        prompt = f"""
        I will create a plan for the following task: {self.plan_description}. 
        I will create a structured plan for a complex task, breaking it down into levels and tasks. 

        IMPORTANT GUIDELINES:
        1. Tasks on the same level execute in parallel and should be independent of each other.
        2. If a task depends on another task, they must be on separate levels.
        3. Outputs of previous levels are fed into the next level. Tasks on one level don't have observability of outputs from other tasks on the same level.
        4. Each task, especially those on the same level, should operate on separate files to avoid conflicts and overwrites.
        5. Clearly specify the input and output files for each task.
        6. Use descriptive and unique filenames for each task's output.
        7. If a task needs to combine or process outputs from previous tasks, it should be on a new level.
        8. Consider creating temporary or intermediate files for complex multi-step processes.

        PLAN STRUCTURE:
        For each task in the plan, include the following information:
        - Task name and description
        - Input files (if any)
        - Output files (clearly specified)
        - Agent type required for the task

        Example task structure:
        {{
        "name": "Analyze Student Data",
        "description": "Process raw student data and generate summary statistics",
        "agent_type": "DataAnalysisAgent",
        "input_files": ["raw_student_data.csv"],
        "output_files": ["student_data_summary.json", "student_performance_metrics.csv"]
        }}

        EXECUTION CONTEXT:
        When I use the delegate_and_execute_task action, the plan will be fully executed before the action completes. The result will provide a detailed summary of the task execution, including the actions taken by other agents.

        After using delegate_and_execute_task, I should evaluate whether the goal has been achieved based on the detailed execution summary provided in the result.
        """
        response = await self.llm.create_chat_completion(
            prompt,
            f"Generate a detailed plan for the task: {self.plan_description}. Ensure each task has clear file inputs and outputs, and that parallel tasks work on separate files.",
            tool_config,
        )

        if response and len(response) > 0:
            return response.get("plan", {})
        else:
            raise ValueError("Failed to generate plan with LLM")

    def _create_plan_from_llm_response(self, llm_response: Dict[str, Any]) -> Plan:
        plan = Plan(self.plan_name, self.plan_description)

        for level_data in llm_response.get("levels", []):
            level = Level(level_data["order"])
            for task_data in level_data.get("tasks", []):
                task = Task(
                    name=task_data["name"],
                    description=task_data["description"],
                    agent_type=task_data["agent_type"],
                    level=level,
                    input_files=task_data.get("input_files", []),
                    output_files=task_data.get("output_files", []),
                )
                level.add_task(task)
            plan.add_level(level)

        return plan
