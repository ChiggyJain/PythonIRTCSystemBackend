
import uuid
from app.infrastructure.payment_gateway.base_payment_gateway import BasePaymentGateway

class RazorpayPaymentGateway(BasePaymentGateway):
    
    def __init__(self, **kwargs):
        pass

    async def createOrder(self, **kwargs):

        try:
            
            amount = kwargs.get("amount", 0)
            currency = kwargs.get("currency", "INR")
            receipt = kwargs.get("receipt", "")
            notes = kwargs.get("notes", {})
            
            return {
                "payment_gateway_order_id" : str(uuid.uuid4()),
                "amount" : amount,
                "currency" : currency,
                "receipt"  : receipt,
                "raw_response" : {}
            }
        
        except Exception as e:
            pass
       
 
    async def verifyPaymentSignature(self, **kwargs):
        pass

    async def verifyWebhookSignature(self, **kwargs):
        pass
    
    async def fetchPayment(self, **kwargs):
        pass