# order-management-system/services/service_service/src/models/api_models.py
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field

class ServiceBase(BaseModel):
    """
    Description:
        Базовая модель задачи, содержащая основные поля задачи.

    Attributes:
        title (str): Заголовок задачи, от 1 до 200 символов.
        description (str): Описание задачи, до 2000 символов.
        priority (servicePriority): Приоритет задачи (по умолчанию - MEDIUM).
    """
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    priority: ServicePriority = Field(default=ServicePriority.MEDIUM)

    class Config:
        from_attributes = True

class ServiceCreate(ServiceBase):
    """
    Description:
        Модель создания задачи, содержащая дополнительное поле order_id и необязательное поле assignee_id.

    Attributes:
        order_id (UUID): Идентификатор проекта, к которому относится задача.
        assignee_id (Optional[UUID]): Идентификатор пользователя, которому назначена задача.
    """
    order_id: UUID
    assignee_id: Optional[UUID] = None

class Service(ServiceBase):
    """
    Description:
        Полная модель задачи, включающая все основные атрибуты, а также статус и временные метки.

    Attributes:
        id (UUID): Уникальный идентификатор задачи.
        status (serviceStatus): Статус задачи (по умолчанию - CREATED).
        order_id (UUID): Идентификатор проекта.
        creator_id (UUID): Идентификатор создателя задачи.
        assignee_id (Optional[UUID]): Идентификатор назначенного пользователя (если имеется).
        created_at (datetime): Дата и время создания задачи.
        updated_at (datetime): Дата и время последнего обновления задачи.

    Config:
        rom_attributes (bool): Разрешает работу с объектами ORM для Pydantic.
    """
    id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    cost: UUID
    creator_id: UUID
    assignee_id: Optional[UUID]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        rom_attributes = True

class ServiceUpdate(BaseModel):
    """
    Description:
        Модель обновления задачи, включающая опциональные поля для обновления.

    Attributes:
        title (Optional[str]): Заголовок задачи, от 1 до 200 символов.
        description (Optional[str]): Описание задачи, до 2000 символов.
        status (Optional[serviceStatus]): Обновленный статус задачи.
        priority (Optional[servicePriority]): Обновленный приоритет задачи.
        assignee_id (Optional[UUID]): Обновленный идентификатор назначенного пользователя.
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    cost: Optional[float] = None
    assignee_id: Optional[UUID] = None

class ServiceResponse(Service):
    """
    Description:
        Модель ответа задачи с дополнительными полями для удобства отображения.
    """

    @classmethod
    def from_mongo(cls, mongo_service: "MongoService") -> "ServiceResponse":
        """
        Преобразует объект Mongoservice в модель serviceResponse.

        Args:
            mongo_service: Объект задачи из базы данных MongoDB.

        Returns:
            Экземпляр serviceResponse.

        Examples:
            >>> mongo_service = MongoService(...)
            >>> service_response = ServiceResponse.from_mongo(mongo_service)
        """
        return cls(
            id          = mongo_service.id,
            title       = mongo_service.title,
            description = mongo_service.description,
            cost        = mongo_service.cost,
            order_id    = mongo_service.order_id,
            creator_id  = mongo_service.creator_id,
            assignee_id = mongo_service.assignee_id,
            created_at  = mongo_service.created_at,
            updated_at  = mongo_service.updated_at,
        )

    class Config:
        """
        Дополнительные настройки модели Pydantic.
        """
        from_attributes = True
