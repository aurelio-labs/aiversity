from abc import ABC, abstractmethod
from typing import Optional, Tuple


class Action(ABC):
    @abstractmethod
    async def execute(self) -> Tuple[bool, Optional[str]]:
        """
        Executes the given action.
        Returns a tuple (success, message):
        - success: A boolean indicating whether the action was successful
        - message: An optional string. If success is False, this contains error information.
                   If success is True, this may contain additional information or be None.
        """
        pass
