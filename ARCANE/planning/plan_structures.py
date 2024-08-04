# File: ARCANE/planning/plan_structures.py

from typing import List, Dict, Any
from datetime import datetime
import uuid

class Task:
    def __init__(self, name: str, description: str, agent_type: str):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.agent_type = agent_type
        self.status = "Pending"
        self.start_time = None
        self.end_time = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }

class Level:
    def __init__(self, order: int):
        self.id = str(uuid.uuid4())
        self.order = order
        self.tasks: List[Task] = []
        self.status = "Pending"
        self.start_time = None
        self.end_time = None

    def add_task(self, task: Task):
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

class Plan:
    def __init__(self, name: str, description: str):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.levels: List[Level] = []
        self.status = "Pending"
        self.creation_time = datetime.now()
        self.last_updated = self.creation_time

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
            "last_updated": self.last_updated.isoformat()
        }