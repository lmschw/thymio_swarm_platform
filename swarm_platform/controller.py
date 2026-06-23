from abc import ABC, abstractmethod

from .state import RobotState
from .command import RobotCommand


class Controller(ABC):

    async def setup(self, robot):
        """Called once before the experiment starts."""
        pass

    @abstractmethod
    async def step(self, state: RobotState) -> RobotCommand:
        """Compute the next command from the current robot state."""
        raise NotImplementedError

    async def cleanup(self, robot):
        """Called once after the experiment finishes."""
        pass