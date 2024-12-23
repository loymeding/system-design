# order-management-system/services/service_service/src/models/mongo_models.py
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from ..models.database_models import ServiceStatus, ServicePriority

class MongoService(BaseModel):
    """
    Description:
        MongoDB модель задачи с поддержкой вложенных документов и индексации.

    Attributes:
        id: Уникальный идентификатор задачи, используется как `_id` в MongoDB.
        title: Краткое название задачи. Минимальная длина — 1 символ, максимальная — 200 символов.
        description: Подробное описание задачи. Максимальная длина — 2000 символов.
        status: Статус задачи, отражает текущее состояние (например, "создано", "выполнено").
        priority: Приоритет задачи, используется для определения важности (например, "низкий", "средний", "высокий").
        order_id: Уникальный идентификатор проекта, к которому относится задача.
        creator_id: Уникальный идентификатор пользователя, создавшего задачу.
        assignee_id: Уникальный идентификатор пользователя, ответственного за выполнение задачи. Может быть `None`.
        created_at: Дата и время создания задачи в формате UTC.
        updated_at: Дата и время последнего обновления задачи в формате UTC.
        metadata: Произвольные дополнительные данные, связанные с задачей, хранятся в формате словаря.
        tags: Список тегов для категоризации или фильтрации задач.
    """

    id: UUID = Field(default_factory=uuid4, alias="_id", description="Уникальный идентификатор задачи")
    title: str = Field(..., min_length=1, max_length=200, description="Название задачи (от 1 до 200 символов)")
    description: str = Field(..., max_length=2000, description="Описание задачи (до 2000 символов)")
    status: ServiceStatus = Field(default=ServiceStatus.CREATED, description="Статус задачи")
    priority: ServicePriority = Field(default=ServicePriority.MEDIUM, description="Приоритет задачи")
    order_id: UUID = Field(..., description="ID проекта, связанного с задачей")
    creator_id: UUID = Field(..., description="ID создателя задачи")
    assignee_id: Optional[UUID] = Field(None, description="ID исполнителя задачи")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Дата создания задачи")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Дата последнего обновления задачи")

    metadata: Dict[str, str] = Field(default_factory=dict, description="Произвольные метаданные задачи")
    tags: List[str] = Field(default_factory=list, description="Список тегов задачи")

    class Config:
        """
        Description:
            Конфигурация модели Pydantic для работы с MongoDB.

        Attributes:
            populate_by_name: Позволяет использовать алиасы при создании объектов.
            json_encoders: Определяет преобразование типов для сериализации.
        """
        populate_by_name = True
        json_encoders = {
            UUID: str,                            # Преобразование UUID в строку для сериализации
            datetime: lambda dt: dt.isoformat(),  # Преобразование даты в ISO формат
        }

    @classmethod
    def from_db(cls, data: Dict) -> Optional["MongoService"]:
        """
        Description:
            Создает экземпляр `Mongoservice` из словаря, полученного из MongoDB.

        Args:
            data: Словарь с данными из MongoDB.

        Returns:
            Экземпляр `Mongoservice`, или `None`, если входные данные пусты.

        Raises:
            ValueError: Если UUID имеет некорректный формат.

        Examples:
            >>> data = {
                "_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Sample service",
                ...
            }
            >>> service = MongoService.from_db(data)
        """
        if not data:
            return None

        # Конвертируем строковые ID в UUID, если необходимо
        for field in ["_id", "order_id", "creator_id", "assignee_id"]:
            if field in data and data[field]:
                try:
                    data[field] = UUID(data[field])
                except ValueError as e:
                    raise ValueError(f"Invalid UUID for field '{field}': {data[field]}") from e

        return cls(**data)