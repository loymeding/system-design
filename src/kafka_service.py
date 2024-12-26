import redis
import json
from models import ServiceDB
from dependencies import SessionLocal
from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC
from confluent_kafka import Producer, Consumer, KafkaError

# Настройка Redis
redis_client = redis.from_url("redis://cache:6379/0", decode_responses=True)


# Kafka Producer
def get_kafka_producer():
    return Producer({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})


# Kafka Consumer
def kafka_consumer_service():
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "service-group",
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([KAFKA_TOPIC])

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(f"Ошибка Kafka: {msg.error()}")
                break

        # Обработка сообщения
        service_data = json.loads(msg.value().decode("utf-8"))
        db = SessionLocal()
        try:
            db_service = ServiceDB(**service_data)
            db.add(db_service)
            db.commit()
            db.refresh(db_service)

            # Обновление кеша
            cache_key = f"services:user_id:{service_data['user_id']}"
            services = db.query(ServiceDB).filter(ServiceDB.user_id == service_data['user_id']).all()
            redis_client.set(cache_key, json.dumps([service.dict() for service in services]))
        finally:
            db.close()

    consumer.close()
