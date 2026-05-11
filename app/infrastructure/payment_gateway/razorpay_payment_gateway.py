
from app.infrastructure.payment_gateway.base_payment_gateway import BasePaymentGateway

class RazorpayPaymentGateway(BasePaymentGateway):
    
    def __init__(self, **kwargs):
        pass

    async def createOrder(self, **kwargs):
        pass
 
    async def verifyPaymentSignature(self, **kwargs):
        pass

    async def verifyWebhookSignature(self, **kwargs):
        pass
    
    async def fetchPayment(self, **kwargs):
        pass