
from abc import ABC, abstractmethod

class OutboxBaseRetryHandler(ABC):
    @abstractmethod
    async def handle(self, **kwargs):
        raise NotImplementedError