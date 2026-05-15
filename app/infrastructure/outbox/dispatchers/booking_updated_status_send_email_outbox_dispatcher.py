
import asyncio
import json
import signal
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.email.provider_factory import get_booking_updated_status_email_sender


settings = get_settings()
shutdown_event = asyncio.Event()

def shutdown_handler():
    app_logger.info(f"Shutdown signal received")
    shutdown_event.set()




async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.KAFKA_BOOKING_UPDATED_STATUS_TOPIC,
        group_id=settings.KAFKA_BOOKING_UPDATED_STATUS_EMAIL_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-booking-updated-status-send-email-consumer",
    )
    await consumer.start()
    email_sender = get_booking_updated_status_email_sender()
    app_logger.info("booking_updated_status_send_email_consumer started")
    try:
        
        while not shutdown_event.is_set():
            try:
                message_batch = await asyncio.wait_for(
                    consumer.getmany(timeout_ms=1000),
                    timeout=2
                )
                for tp, messages in message_batch.items():
                    for message in messages:
                        
                        if shutdown_event.is_set():
                            break
                        
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
                        html_content = f"""
                            <html>
                                <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                                    <h2 style="color: #d9534f;">
                                        Booking Status Updated
                                    </h2>
                                    <p>
                                        Your booking-id: <strong>{booking_id} </strong> status has been updated to:
                                        <strong style="color: red;">{booking_status}</strong>
                                    </p>
                                    <h3>Booking Details</h3>
                                    <table 
                                        style="border-collapse: collapse;width: 400px;"
                                        border="1"
                                        cellpadding="10"
                                    >
                                        <tr>
                                            <td><strong>Booking ID:</strong></td>
                                            <td>{booking_id}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>Status:</strong></td>
                                            <td style="color: red;">
                                                {booking_status}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td><strong>Reason:</strong></td>
                                            <td>{booking_status_reason}</td>
                                        </tr>
                                    </table>
                                    <br>
                                    <p>
                                        Thank you for using <strong>IRTC</strong>.
                                    </p>
                                </body>
                            </html>
                        """

                        # Send email with retry
                        email_sent = False
                        for attempt in range(settings.BOOKING_UPDATED_STATUS_EMAIL_MAX_RETRIES + 1):
                            result = await email_sender.send_email(
                                to_email=user_email,
                                subject=subject,
                                html_content=html_content,
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
                            await consumer.commit()
                            print(f"Email send failed after {settings.BOOKING_UPDATED_STATUS_EMAIL_MAX_RETRIES + 1} attempts for booking {booking_id}")
            
            except asyncio.TimeoutError:
                continue    
            except Exception as exc:
                print(f"booking_updated_status_send_email_consumer error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        app_logger.info(
            "Gracefully shutting down"
        )
        await consumer.stop()
        app_logger.info(
            "Shutdown completed"
        )


async def main():
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(
        signal.SIGINT,
        shutdown_handler
    )
    loop.add_signal_handler(
        signal.SIGTERM,
        shutdown_handler
    )
    await run_worker()


if __name__ == "__main__":
    asyncio.run(main())