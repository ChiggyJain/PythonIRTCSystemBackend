
from abc import ABC, abstractmethod

class BaseRetryHandler(ABC):
    @abstractmethod
    async def handle(self, **kwargs):
        raise NotImplementedError