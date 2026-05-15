
from app.infrastructure.outbox.retry_handlers.emailchanged_otp_outbox_retryhandler import EmailChangedOtpOutboxRetryHandler
from app.infrastructure.outbox.retry_handlers.emailverification_otp_outbox_retryhandler import EmailVerificationOtpOutboxRetryHandler
from app.infrastructure.outbox.retry_handlers.pwdchanged_otp_outbox_retryhandler import PwdChangedOtpOutboxRetryHandler
from app.infrastructure.outbox.retry_handlers.stations_outbox_retryhandler import MasterDataStationsOutboxRetryHandler
from app.infrastructure.outbox.retry_handlers.routes_outbox_retryhandler import MasterDataRoutesOutboxRetryHandler
from app.infrastructure.outbox.retry_handlers.schedules_outbox_retryhandler import MasterDataSchedulesOutboxRetryHandler
from app.infrastructure.outbox.retry_handlers.schedule_inventory_seat_availability_updated_outbox_retryhandler import ScheduleInventorySeatAvailabilityUpdatedOutboxRetryHandler
from app.infrastructure.outbox.retry_handlers.payment_orders_updated_status_outbox_retryhandler import PaymentOrdersUpdatedStatusOutboxRetryHandler
from app.infrastructure.outbox.retry_handlers.booking_updated_status_outbox_retryhandler import BookingUpdatedStatusOutboxRetryHandler

class OutboxRetryHandlerFactory:

    _handlers = {
        "EMAILCHANGED_OTP": EmailChangedOtpOutboxRetryHandler,
        "EMAILVERIFICATION_OTP": EmailVerificationOtpOutboxRetryHandler,
        "PWDCHANGED_OTP": PwdChangedOtpOutboxRetryHandler,
        "STATIONS": MasterDataStationsOutboxRetryHandler,
        "ROUTES": MasterDataRoutesOutboxRetryHandler,
        "SCHEDULES": MasterDataSchedulesOutboxRetryHandler,
        "SCHEDULE_INVENTORY_SEAT_AVAILABILITY_UPDATED" : ScheduleInventorySeatAvailabilityUpdatedOutboxRetryHandler,
        "PAYMENT_ORDERS_UPDATED_STATUS" : PaymentOrdersUpdatedStatusOutboxRetryHandler,
        "BOOKING_UPDATED_STATUS" : BookingUpdatedStatusOutboxRetryHandler,
    }

    @staticmethod
    def get_outbox_retry_handler(**kwargs):
        retry_handler_type = kwargs.get("retry_handler_type")
        handler_class = OutboxRetryHandlerFactory._handlers.get(retry_handler_type)
        if not handler_class:
            raise ValueError(f"Unsupported retry_handler_type: {retry_handler_type}")
        return handler_class(**kwargs)