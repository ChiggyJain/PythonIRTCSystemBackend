
import asyncio
import json
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.email.provider_factory import get_booking_updated_status_email_sender


settings = get_settings()



async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.KAFKA_BOOKING_UPDATED_STATUS_TOPIC,
        group_id=settings.KAFKA_BOOKING_UPDATED_STATUS_EMAIL_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-booking-updated-status-send-email-consumer",
    )
    await consumer.start()
    app_logger.info("booking_updated_status_send_email_consumer started")
    try:
        email_sender = get_booking_updated_status_email_sender()
        async for message in consumer:
            try:
                
                payload = json.loads(message.value.decode("utf-8"))
                topic_name = message.topic
                print(f"Topic: {topic_name}, Payload: {payload}")

                # extract booking details
                booking_id = payload.get("booking_id")
                booking_status = payload.get("booking_status")
                user_email = payload.get("user_email")
                booking_status_reason = payload.get("booking_status_reason", "N/A")
                
                if not user_email:
                    print(f"No user email in booking updated status payload")
                    await consumer.commit()
                    continue

                # Build email content
                subject = f"{settings.BOOKING_UPDATED_STATUS_EMAIL_SUBJECT_PREFIX} - {booking_status}"
                body = f"""
                    Your booking {booking_id} status has been updated to: {booking_status}
                    Booking Details:
                    - Booking ID: {booking_id}
                    - Status: {booking_status}
                    - Reason: {booking_status_reason}
                    Thank you for using IRTC.
                    """

                # Send email with retry
                email_sent = False
                for attempt in range(settings.BOOKING_UPDATED_STATUS_EMAIL_MAX_RETRIES + 1):
                    result = await email_sender.send_email(
                        to_email=user_email,
                        subject=subject,
                        plain_text_content=body,
                    )  
                    if result.accepted:
                        print(f"Email sent successfully for booking {booking_id} on attempt {attempt + 1}")
                        email_sent = True
                        break
                    else:
                        print(f"Email send attempt {attempt + 1} failed for booking {booking_id}: {result.error_message}")
                        if attempt < settings.BOOKING_UPDATED_STATUS_EMAIL_MAX_RETRIES:
                            await asyncio.sleep(settings.BOOKING_UPDATED_STATUS_EMAIL_RETRY_DELAY_SECONDS)                
                if not email_sent:
                    print(f"Email send failed after {settings.BOOKING_UPDATED_STATUS_EMAIL_MAX_RETRIES + 1} attempts for booking {booking_id}")

                await consumer.commit()
                
            except Exception as exc:
                print(f"booking_updated_status_send_email_consumer error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
