
import uuid
import time
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
            # dummy order response from razor payy
            order_response  = {
                "amount": amount,
                "amount_due": amount,
                "amount_paid": 0,
                "attempts": 0,
                "created_at": int(time.time()),
                "currency": "INR",
                "entity": "order",
                "id": str(uuid.uuid4()),
                "notes": notes,
                "offer_id": None,
                "receipt": receipt,
                "status": "created"
            }

            # hardcoded dummy response
            return {
                "status_code" : 201,
                "messages" : [f"Payment gateway created order request successfully"],
                "payment_gateway_order_id" : order_response["id"],
                "amount" : order_response["amount"],
                "currency" : order_response["currency"],
                "receipt"  : order_response["receipt"],
                "raw_response" : order_response
            }
        
        except Exception as e:
            return {
                "status_code" : 500,
                "messages" : [f"{str(e)}"],
            }
       
 

    async def verifyPaymentSignature(self, **kwargs):
        pass

    async def verifyWebhookSignature(self, **kwargs):
        pass
    
    async def fetchPayment(self, **kwargs):
        pass


    async def initiateRefund(self, **kwargs):

        try:
            
            # extracted parameters
            payment_id = kwargs.get("payment_id", "")
            amount = kwargs.get("amount", 0)
            notes = kwargs.get("notes", {})
            
            # actual razorpay implementation business logic will be come here
            # dummy order response from razor payy
            refund_response  = {
                "amount": amount,
                "amount_due": amount,
                "amount_paid": 0,
                "attempts": 0,
                "created_at": int(time.time()),
                "currency": "INR",
                "entity": "order",
                "id": str(uuid.uuid4()),
                "notes": notes,
                "offer_id": None,
                "status": "created"
            }

            # hardcoded dummy response
            return {
                "status_code" : 200,
                "messages" : [f"Payment gateway order refunded successfully"],
                "payment_gateway_refund_id" : refund_response["id"],
                "status" : refund_response["status"],
                "amount" : refund_response["amount"],
                "raw_response" : refund_response
            }
        
        except Exception as e:
            return {
                "status_code" : 500,
                "messages" : [f"{str(e)}"],
            }