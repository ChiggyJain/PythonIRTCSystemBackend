

from app.infrastructure.outbox.retry_handlers.emailchanged_otp_outbox_retryhandler import EmailChangedOtpOutboxRetryHandler


class OutboxRetryHandlerFactory:

    @staticmethod
    def getOutboxRetryHandler(**kwargs):
        retry_handler_type =  kwargs.get("retry_handler_type", None)
        if retry_handler_type == "EMAILCHANGED_OTP":
            return EmailChangedOtpOutboxRetryHandler(**kwargs)