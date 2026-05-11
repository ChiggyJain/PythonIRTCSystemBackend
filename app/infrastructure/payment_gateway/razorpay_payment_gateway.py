
import uuid
from app.core.exceptions import BaseAppException
from app.core.response import (
    standardize_response, 
)
from app.infrastructure.payment_gateway.base_payment_gateway import BasePaymentGateway


class RazorpayPaymentGateway(BasePaymentGateway):
    
    def __init__(self, **kwargs):
        pass

    async def createOrder(self, **kwargs):

        try:
            
            # extracted parameters
            amount = kwargs.get("amount", 0)
            currency = kwargs.get("currency", "INR")
            receipt = kwargs.get("receipt", "")
            notes = kwargs.get("notes", {})
            
            # actual razorpay implementation business logic will be come here

            # hardcoded dummy response is returning always with unique-ID into payment_gateway_order_id field
            return standardize_response(
                status_code=201,
                messages=[f"Payment gateway created order request successfully"],
                data={
                    "payment_gateway_order_id" : str(uuid.uuid4()),
                    "amount" : amount,
                    "currency" : currency,
                    "receipt"  : receipt,
                    "raw_response" : {}
                }
            )
        
        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"],
            )
       
 
    async def verifyPaymentSignature(self, **kwargs):
        pass

    async def verifyWebhookSignature(self, **kwargs):
        pass
    
    async def fetchPayment(self, **kwargs):
        pass