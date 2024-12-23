# order-management-system/services/service_service/src/services/command_service.py

# Стандартные библиотеки
import logging
from typing import Dict, Any
from uuid import UUID, uuid4

# Локальные импорты
from ..events.kafka_producer import KafkaServiceProducer
from ..models.api_models import ServiceCreate, ServiceUpdate

# Настройка логирования
logger = logging.getLogger(__name__)


class ServiceCommandService:
    """
    Description:
        Сервис для обработки команд, связанных с задачами.
        Управляет созданием и обновлением задач через события Kafka.

    Args:
        kafka_producer: Производитель событий Kafka

    Examples:
        >>> service = ServiceCommandService(kafka_producer)
        >>> service = await service.create_service(service_data, creator_id)
    """

    def __init__(self, kafka_producer: KafkaServiceProducer) -> None:
        self.kafka_producer: KafkaServiceProducer = kafka_producer

    async def create_service(
        self,
        service_data: ServiceCreate,
        creator_id: UUID
    ) -> Dict[str, Any]:
        """
        Description:
            Создает новую задачу и отправляет событие в Kafka.

        Args:
            service_data: Данные для создания задачи
            creator_id: Идентификатор создателя задачи

        Returns:
            Dict[str, Any]: Словарь с данными созданной задачи

        Raises:
            Exception: При ошибке создания задачи

        Examples:
            >>> service = await service.create_service(
            ...     serviceCreate(title="New service"),
            ...     UUID("123...")
            ... )
        """
        try:
            service_dict = service_data.dict()
            service_dict["creator_id"] = creator_id
            service_dict["id"] = str(uuid4())
            
            await self.kafka_producer.send_service_created_event(service_dict)
            
            return service_dict
        except Exception as e:
            logger.error(f"Error in create_service command: {str(e)}")
            raise