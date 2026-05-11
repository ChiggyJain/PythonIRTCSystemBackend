
from abc import ABC, abstractmethod

class BasePaymentGateway(ABC):
    
    @abstractmethod
    async def createOrder(self, **kwargs):
        pass

    @abstractmethod
    async def verifyPaymentSignature(self, **kwargs):
        pass

    @abstractmethod
    async def verifyWebhookSignature(self, **kwargs):
        pass

    @abstractmethod
    async def fetchPayment(self, **kwargs):
        pass