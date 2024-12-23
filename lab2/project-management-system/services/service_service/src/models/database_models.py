# order-management-system/services/service_service/src/models/database_models.py
import uuid
import enum
from utils.database import Base

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class ServiceStatus(str, enum.Enum):
    """
    Description:
        Enum, представляющий возможные статусы задачи.
    """
    CREATED     = "created"
    IN_PROGRESS = "in_progress"
    ON_REVIEW   = "on_review"
    COMPLETED   = "completed"

class ServicePriority(str, enum.Enum):
    """
    Description:
        Enum, представляющий приоритеты задачи.
    """
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"

class Service(Base):
    """
    Description:
        Модель для представления задачи в системе управления проектами.

    Attributes:
        id (UUID): Уникальный идентификатор задачи.
        title (str): Название задачи, краткое описание.
        description (str): Полное описание задачи.
        status (serviceStatus): Статус задачи (например, создана, в процессе, на проверке, завершена).
        priority (servicePriority): Приоритет задачи (низкий, средний, высокий).
        order_id (UUID): Внешний ключ к проекту, к которому относится задача.
        creator_id (UUID): Внешний ключ к создателю задачи (пользователь, который создал).
        assignee_id (UUID): Внешний ключ к исполнителю задачи (пользователь, который выполняет).
        created_at (DateTime): Время создания задачи.
        updated_at (DateTime): Время последнего обновления задачи.
    """
    
    __tablename__ = "services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(SQLAlchemyEnum(ServiceStatus), default=ServiceStatus.CREATED, nullable=False)
    priority = Column(SQLAlchemyEnum(ServicePriority), default=ServicePriority.MEDIUM, nullable=False)
    
    order_id = Column(UUID(as_uuid=True), nullable=False)
    creator_id = Column(UUID(as_uuid=True), nullable=False)
    assignee_id = Column(UUID(as_uuid=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        """
        Description:
            Возвращает строковое представление объекта service.

        Returns:
            str: Строковое представление объекта service с id и названием задачи.
        """
        return f"<service(id={self.id}, title={self.title})>"
