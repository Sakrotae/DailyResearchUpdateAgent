from abc import ABC, abstractmethod

class BaseAgent(ABC):
    @abstractmethod
    async def execute_task(self, task_input: dict) -> dict:
        '''
        Executes the agent's specific task.
        Input and output are dictionaries for flexibility.
        Should be implemented as an async method if it involves I/O.
        '''
        pass

class AgentOutput:
    def __init__(self, success: bool, data: dict = None, error_message: str = None):
        self.success = success
        self.data = data if data is not None else {}
        self.error_message = error_message

    def to_dict(self):
        return {
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message
        }
