
from app.infrastructure.payment_gateway.razorpay_payment_gateway import RazorpayPaymentGateway

class PaymentGatewayFactory:

    _instances = {
        "razorpay": RazorpayPaymentGateway,
    }

    @staticmethod()
    def getPaymentGatewayInstances(**kwargs):
        payment_gateway_service_provider = kwargs.get("payment_gateway_service_provider")
        instances_class = PaymentGatewayFactory._instances.get(payment_gateway_service_provider)
        if not instances_class:
            raise ValueError(f"Unsupported payment gateway service provider: {payment_gateway_service_provider}")
        return instances_class(**kwargs)