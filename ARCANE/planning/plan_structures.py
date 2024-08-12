from typing import List, Dict, Any
from datetime import datetime
import uuid

class Task:
    def __init__(self, name: str, description: str, agent_type: str, task_id: str = None, level: 'Level' = None, input_files: List[str] = None, output_files: List[str] = None):
        self.id = task_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.agent_type = agent_type
        self.status = "Pending"
        self.start_time = None
        self.end_time = None
        self.output_message: str = None
        self.output_files: List[Dict[str, str]] = []
        self.level = level
        self.input_files = input_files or []
        self.output_files = output_files or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "output_message": self.output_message,
            "output_files": self.output_files,
            "level_order": self.level.order if self.level else None,
            "input_files": self.input_files,
            "output_files": self.output_files,
        }


    @classmethod
    def from_dict(cls, data: Dict[str, Any], level: 'Level' = None) -> 'Task':
        task = cls(
            data['name'], 
            data['description'], 
            data['agent_type'], 
            data['id'], 
            level,
            data.get('input_files', []),
            data.get('output_files', [])
        )
        task.status = data['status']
        task.start_time = datetime.fromisoformat(data['start_time']) if data['start_time'] else None
        task.end_time = datetime.fromisoformat(data['end_time']) if data['end_time'] else None
        task.output_message = data.get('output_message')
        task.output_files = data.get('output_files', [])
        return task

class Level:
    def __init__(self, order: int, level_id: str = None):
        self.id = level_id or str(uuid.uuid4())
        self.order = order
        self.tasks: List[Task] = []
        self.status = "Pending"
        self.start_time = None
        self.end_time = None

    def add_task(self, task: Task):
        task.level = self  # Set the parent Level reference
        self.tasks.append(task)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order": self.order,
            "tasks": [task.to_dict() for task in self.tasks],
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Level':
        level = cls(data['order'], data['id'])
        level.tasks = [Task.from_dict(task_data, level) for task_data in data['tasks']]
        level.status = data['status']
        level.start_time = datetime.fromisoformat(data['start_time']) if data['start_time'] else None
        level.end_time = datetime.fromisoformat(data['end_time']) if data['end_time'] else None
        return level

class Plan:
    def __init__(self, name: str, description: str, plan_id: str = None):
        self.id = plan_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.levels: List[Level] = []
        self.status = "Pending"
        self.creation_time = datetime.now()
        self.last_updated = self.creation_time
        self.work_directory: str = None

    def add_level(self, level: Level):
        self.levels.append(level)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "levels": [level.to_dict() for level in self.levels],
            "status": self.status,
            "creation_time": self.creation_time.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "work_directory": self.work_directory
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        plan = cls(data['name'], data['description'], data['id'])
        plan.levels = [Level.from_dict(level_data) for level_data in data['levels']]
        plan.status = data['status']
        plan.creation_time = datetime.fromisoformat(data['creation_time'])
        plan.last_updated = datetime.fromisoformat(data['last_updated'])
        plan.work_directory = data.get('work_directory')
        return plan