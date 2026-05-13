"""
Kafka client builders.
"""

from aiokafka import (
    AIOKafkaProducer, AIOKafkaConsumer
)
from app.core.settings import get_settings


_settings = get_settings()


def build_producer(
    *,
    client_id: str,
) -> AIOKafkaProducer:
    return AIOKafkaProducer(
        bootstrap_servers=_settings.KAFKA_BOOTSTRAP_SERVERS,
        client_id=client_id,
        acks="all",
        linger_ms=10,
        enable_idempotence=True,
    )


def build_consumer(
    *,
    topic: str | list[str],
    group_id: str,
    client_id: str,
) -> AIOKafkaConsumer:
    
    topics = [topic] if isinstance(topic, str) else topic
    return AIOKafkaConsumer(
        *topics,
        bootstrap_servers=_settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=group_id,
        client_id=client_id,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        max_poll_records=50,
    )
