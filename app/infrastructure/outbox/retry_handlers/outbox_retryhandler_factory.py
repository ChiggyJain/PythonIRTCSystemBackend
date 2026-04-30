

from app.infrastructure.outbox.retry_handlers.emailchanged_otp_outbox_retryhandler import EmailChangedOtpOutboxRetryHandler
from app.infrastructure.outbox.retry_handlers.emailverification_otp_outbox_retryhandler import EmailVerificationOtpOutboxRetryHandler
from app.infrastructure.outbox.retry_handlers.pwdchanged_otp_outbox_retryhandler import PwdChangedOtpOutboxRetryHandler
from app.infrastructure.outbox.retry_handlers.masterdata_stations_outbox_retryhandler import MasterDataStationsOutboxRetryHandler


class OutboxRetryHandlerFactory:

    @staticmethod
    def getOutboxRetryHandler(**kwargs):
        retry_handler_type =  kwargs.get("retry_handler_type", None)
        if retry_handler_type == "EMAILCHANGED_OTP":
            return EmailChangedOtpOutboxRetryHandler(**kwargs)
        if retry_handler_type == "EMAILVERIFICATION_OTP":
            return EmailVerificationOtpOutboxRetryHandler(**kwargs)
        if retry_handler_type == "PWDCHANGED_OTP":
            return PwdChangedOtpOutboxRetryHandler(**kwargs)
        if retry_handler_type == "MASTERDATA_STATIONS":
            return MasterDataStationsOutboxRetryHandler(**kwargs)