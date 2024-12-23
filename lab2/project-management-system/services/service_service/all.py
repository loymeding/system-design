# order-management-system/services/service_service/run.py
import sys
from pathlib import Path

# Добавляем путь к корню проекта
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

import uvicorn
from service_service.src.main import app

if __name__ == "__main__":
    uvicorn.run(
        "service_service.src.main:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )

# order-management-system/services/service_service/src/main.py

# --- Импорты сторонних библиотек ---
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Импорты модулей проекта ---
from .api import routes
from .database import db

import json
import logging
from typing import Dict, Any
from aiokafka import AIOKafkaConsumer
from motor.motor_asyncio import AsyncIOMotorClient

# Инициализация FastAPI приложения
app = FastAPI(title="service Service", description="API для управления задачами")

logger = logging.getLogger(__name__)

# --- Настройка CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Подключение маршрутов ---
app.include_router(routes.router)

class ServiceEventHandler:
    def __init__(self, bootstrap_servers: str, topic: str, mongodb_url: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.mongodb_url = mongodb_url
        self.consumer = None
        self.db = None

    async def start(self):
        # Инициализация MongoDB
        client = AsyncIOMotorClient(self.mongodb_url)
        self.db = client.service_service.services

        # Инициализация Kafka Consumer
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await self.consumer.start()
        logger.info("service event handler started")

        try:
            async for msg in self.consumer:
                await self.handle_event(msg.value)
        finally:
            await self.consumer.stop()

    async def handle_event(self, event: Dict[str, Any]):
        try:
            if event["event_type"] == "service_created":
                await self.handle_service_created(event["data"])
        except Exception as e:
            logger.error(f"Error handling event: {str(e)}")

    async def handle_service_created(self, service_data: Dict[str, Any]):
        try:
            await self.db.insert_one(service_data)
            logger.info(f"service created in database: {service_data.get('id')}")
        except Exception as e:
            logger.error(f"Error saving service to database: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """
    Description:
        Функция, выполняемая при запуске приложения. Инициализирует подключение к базе данных.
    """
    print("service Service started")
    try:
        # Инициализируем подключение к БД
        db.connect()
        print("service Service - Database connected successfully")

        # Инициализация Kafka producer
        app.state.kafka_producer = KafkaServiceProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            topic=settings.KAFKA_SERVICE_TOPIC
        )
        await app.state.kafka_producer.start()
        print("service Service - KafkaserviceProducer connected successfully")

    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """
    Description:
        Функция, выполняемая при остановке приложения. Закрывает подключение к базе данных.
    """
    try:
        # Закрываем подключение к БД
        db.disconnect()
        print("Database connection closed")
        await app.state.kafka_producer.stop()
        print("Kafka_producer connection closed")
    except Exception as e:
        print(f"Error disconnecting from database: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

# order-management-system/services/service_service/src/database.py

# Испорт стандартных библиотек
import logging
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any

# Импорт сторонних библиотек
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
from bson import UuidRepresentation

# Импорт библиотек проекта
from utils.database import db_manager
from .models.mongo_models import MongoService
from .core.config import MONGODB_URL, MONGODB_DB_NAME

# Logging setup
logger = logging.getLogger(__name__)

class MongoDBManager:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.services = None

    async def connect(self) -> None:
        try:
            self.client = AsyncIOMotorClient(
                MONGODB_URL,
                uuidRepresentation='standard'
            )
            self.db = self.client[MONGODB_DB_NAME]
            self.services = self.db.services
            await self.ensure_indexes()
            logger.info("Подключение к MongoDB успешно выполнено.")
            return self  # Возвращаем self для цепочки вызовов
        except Exception as e:
            logger.error(f"Ошибка подключения к MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        if self.client:
            self.client.close()
            logger.info("Соединение с MongoDB закрыто.")

    async def ensure_indexes(self) -> None:
        try:
            indexes = [
                IndexModel([("order_id", ASCENDING)]),
                IndexModel([("creator_id", ASCENDING)]),
                IndexModel([("assignee_id", ASCENDING)]),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("priority", ASCENDING)]),
                IndexModel([
                    ("order_id", ASCENDING),
                    ("status", ASCENDING),
                    ("priority", DESCENDING)
                ]),
                IndexModel([("created_at", DESCENDING)]),
                IndexModel([("tags", ASCENDING)])
            ]
            await self.services.create_indexes(indexes)
            logger.info("Индексы успешно созданы.")
        except Exception as e:
            logger.error(f"Ошибка создания индексов: {e}")
            raise

    async def create_service(self, service: MongoService) -> MongoService:
        try:
            service_dict = service.model_dump(by_alias=True)
            logger.debug(f"Преобразование Mongoservice в словарь: {service_dict}")

            mongo_dict = self._convert_uuids_to_str(service_dict)
            result = await self.services.insert_one(mongo_dict)

            saved_doc = await self.services.find_one({"_id": result.inserted_id})
            if not saved_doc:
                raise Exception("Документ не найден после вставки.")

            saved_service = MongoService(**self._convert_ids_to_uuid(saved_doc))
            logger.info("Задача успешно создана.")
            return saved_service
        except Exception as e:
            logger.error(f"Ошибка создания задачи: {e}")
            raise

    async def get_service(self, service_id: UUID) -> Optional[MongoService]:
        try:
            service_dict = await self.services.find_one({"_id": str(service_id)})
            if service_dict:
                return MongoService(**self._convert_ids_to_uuid(service_dict))
            return None
        except Exception as e:
            logger.error(f"Ошибка получения задачи: {e}")
            raise

    async def update_service(self, service_id: UUID, update_data: Dict[str, Any]) -> Optional[Mongoservice]:
        try:
            update_data["updated_at"] = datetime.utcnow()
            update_data = self._convert_uuids_to_str(update_data)

            result = await self.services.update_one(
                {"_id": str(service_id)},
                {"$set": update_data}
            )
            if result.modified_count:
                return await self.get_service(service_id)
            return None
        except Exception as e:
            logger.error(f"Ошибка обновления задачи: {e}")
            raise

    async def delete_service(self, service_id: UUID) -> bool:
        try:
            result = await self.services.delete_one({"_id": str(service_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Ошибка удаления задачи: {e}")
            raise

    def _convert_uuids_to_str(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: (str(value) if isinstance(value, UUID) else value)
            for key, value in data.items()
        }

    def _convert_ids_to_uuid(self, data: Dict[str, Any]) -> Dict[str, Any]:
        for field in ["_id", "order_id", "creator_id", "assignee_id"]:
            if field in data and data[field]:
                data[field] = UUID(data[field])
        return data
    
# Реэкспорт db_manager для обратной совместимости
db = db_manager

# order-management-system/services/service_service/src/auth.py

# --- Импорты стандартных библиотек ---
import os
from datetime import datetime, timedelta

# --- Импорты сторонних библиотек ---
from dotenv import load_dotenv
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from uuid import UUID
import httpx

# Загрузка переменных окружения
load_dotenv()

# --- Настройки JWT ---
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")

# --- Настройка OAuth2 ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    id: UUID
    username: str
    email: str
    is_active: bool

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{USER_SERVICE_URL}/users/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    user_data = response.json()
                    return User(**user_data)
                else:
                    raise credentials_exception
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"User service unavailable: {str(e)}"
                )
    except JWTError:
        raise credentials_exception

# order-management-system/services/service_service/src/services/command_service.py
from typing import Optional
from uuid import UUID
import logging
from ..models.api_models import ServiceCreate, ServiceUpdate
from ..events.kafka_producer import KafkaServiceProducer

logger = logging.getLogger(__name__)

class ServiceCommandService:
    def __init__(self, kafka_producer: KafkaServiceProducer):
        self.kafka_producer = kafka_producer

    async def create_service(self, service_data: ServiceCreate, creator_id: UUID) -> Dict[str, Any]:
        try:
            service_dict = service_data.dict()
            service_dict["creator_id"] = creator_id
            service_dict["id"] = str(UUID.uuid4())
            
            # Отправляем событие в Kafka
            await self.kafka_producer.send_service_created_event(service_dict)
            
            return service_dict
        except Exception as e:
            logger.error(f"Error in create_service command: {str(e)}")
            raise

# order-management-system/services/service_service/src/services/query_service.py
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
from ..models.mongo_models import MongoService
from ..database import MongoDBManager

logger = logging.getLogger(__name__)

class ServiceQueryService:
    def __init__(self, db_manager: MongoDBManager):
        self.db = db_manager

    async def get_service(self, service_id: UUID) -> Optional[MongoService]:
        try:
            return await self.db.get_service(service_id)
        except Exception as e:
            logger.error(f"Error in get_service query: {str(e)}")
            raise

    async def get_services_by_criteria(self, criteria: Dict[str, Any]) -> List[MongoService]:
        try:
            return await self.db.get_services_by_criteria(criteria)
        except Exception as e:
            logger.error(f"Error in get_services_by_criteria query: {str(e)}")
            raise

# order-management-system/services/service_service/src/services/service_service.py
# Импорт стандартных библиотек
import logging
from uuid import UUID
from typing import List, Optional, Dict, Any

# order imports
from ..models.mongo_models import MongoService
from ..models.api_models import ServiceCreate, EerviceUpdate

# Настройка логирования
logger = logging.getLogger(__name__)

class ServiceService:
    
    def __init__(self, db_manager):
        self.db = db_manager

    async def create_service(self, service_data: ServiceCreate, creator_id: UUID) -> Mongoservice:
        try:
            logger.info("Начало создания задачи в serviceService")
            logger.debug(f"Данные задачи: {service_data.model_dump_json(indent=2)}")
            logger.debug(f"ID создателя: {creator_id}")

            service = MongoService(
                title=service_data.title,
                description=service_data.description,
                priority=service_data.priority,
                order_id=service_data.order_id,
                creator_id=creator_id,
                assignee_id=service_data.assignee_id
            )
            logger.debug(f"Создан объект Mongoservice: {service.model_dump_json(indent=2)}")

            # Сохранение задачи в базе данных
            try:
                saved_service = await self.db.create_service(service)
                logger.info(f"Задача успешно сохранена: {saved_service.model_dump_json(indent=2)}")
                return saved_service
            except Exception as e:
                logger.error(f"Ошибка сохранения задачи в MongoDB: {str(e)}")
                raise Exception("Ошибка сохранения задачи в базу данных") from e

        except Exception as e:
            logger.error(f"Ошибка в serviceService.create_service: {str(e)}")
            raise

    async def update_service(self, service_id: UUID, service_update: ServiceUpdate) -> Optional[Mongoservice]:
        try:
            update_data = service_update.dict(exclude_unset=True)
            updated_service = await self.db.update_service(service_id, update_data)
            logger.info(f"Задача {service_id} успешно обновлена.")
            return updated_service
        except Exception as e:
            logger.error(f"Ошибка обновления задачи: {str(e)}")
            raise

    async def delete_service(self, service_id: UUID) -> bool:
        try:
            is_deleted = await self.db.delete_service(service_id)
            if is_deleted:
                logger.info(f"Задача {service_id} успешно удалена.")
            else:
                logger.warning(f"Задача {service_id} не найдена для удаления.")
            return is_deleted
        except Exception as e:
            logger.error(f"Ошибка удаления задачи: {str(e)}")
            raise

    async def get_order_services(self, order_id: UUID) -> List[MongoService]:
        try:
            services = await self.db.get_services_by_order(order_id)
            logger.info(f"Найдено {len(services)} задач для проекта {order_id}.")
            return services
        except Exception as e:
            logger.error(f"Ошибка получения задач проекта: {str(e)}")
            raise

    async def get_services_by_criteria(self, criteria: Dict[str, Any]) -> List[MongoService]:
        try:
            services = await self.db.get_services_by_criteria(criteria)
            logger.info(f"Найдено {len(services)} задач по критериям {criteria}.")
            return services
        except Exception as e:
            logger.error(f"Ошибка получения задач по критериям: {str(e)}")
            raise

# order-management-system/services/service_service/src/models/api_models.py
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field
from .database_models import ServiceStatus, ServicePriority

class ServiceBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    priority: ServicePriority = Field(default=ServicePriority.MEDIUM)

    class Config:
        from_attributes = True

class ServiceCreate(ServiceBase):
    order_id: UUID
    assignee_id: Optional[UUID] = None

class Service(ServiceBase):
    id: UUID = Field(default_factory=uuid4)
    status: ServiceStatus = Field(default=ServiceStatus.CREATED)
    order_id: UUID
    creator_id: UUID
    assignee_id: Optional[UUID]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        rom_attributes = True

class ServiceUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[ServiceStatus] = None
    priority: Optional[ServicePriority] = None
    assignee_id: Optional[UUID] = None

class ServiceResponse(Service):

    @classmethod
    def from_mongo(cls, mongo_service: "MongoService") -> "ServiceResponse":
        return cls(
            id          = mongo_service.id,
            title       = mongo_service.title,
            description = mongo_service.description,
            status      = mongo_service.status,
            priority    = mongo_service.priority,
            order_id  = mongo_service.order_id,
            creator_id  = mongo_service.creator_id,
            assignee_id = mongo_service.assignee_id,
            created_at  = mongo_service.created_at,
            updated_at  = mongo_service.updated_at,
        )

    class Config:
        from_attributes = True

# order-management-system/services/service_service/src/models/database_models.py
import uuid
import enum
from utils.database import Base

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class ServiceStatus(str, enum.Enum):
    CREATED     = "created"
    IN_PROGRESS = "in_progress"
    ON_REVIEW   = "on_review"
    COMPLETED   = "completed"

class ServicePriority(str, enum.Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"

class Service(Base):
    
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
        return f"<service(id={self.id}, title={self.title})>"

# order-management-system/services/service_service/src/models/mongo_models.py
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from ..models.database_models import ServiceStatus, ServicePriority

class MongoService(BaseModel):

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
        populate_by_name = True
        json_encoders = {
            UUID: str,                            # Преобразование UUID в строку для сериализации
            datetime: lambda dt: dt.isoformat(),  # Преобразование даты в ISO формат
        }

    @classmethod
    def from_db(cls, data: Dict) -> Optional["Mongoservice"]:
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
    
# order-management-system/services/service_service/src/events/kafka_producer.py
from aiokafka import AIOKafkaProducer
import json
import logging
from typing import Any, Dict
from uuid import UUID

logger = logging.getLogger(__name__)

class KafkaServiceProducer:
    def __init__(self, bootstrap_servers: str, topic: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
        await self.producer.start()
        logger.info(f"Kafka producer started: {self.bootstrap_servers}")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def send_service_created_event(self, service_data: Dict[str, Any]):
        if not self.producer:
            raise RuntimeError("Producer not started")
        
        try:
            event = {
                "event_type": "service_created",
                "data": service_data
            }
            await self.producer.send_and_wait(self.topic, event)
            logger.info(f"service created event sent: {service_data.get('id')}")
        except Exception as e:
            logger.error(f"Error sending service created event: {str(e)}")
            raise

# order-management-system/services/service_service/src/core/config.py

# Импорты библиотек
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения или .env файла.
    """

    # Настройки MongoDB
    MONGODB_URL: str     = Field(default="mongodb://mongodb:27017", description="URL для подключения к MongoDB")
    MONGODB_DB_NAME: str = Field(default="service_service", description="Имя базы данных MongoDB")

    # URL других сервисов
    USER_SERVICE_URL: str    = Field(default="http://localhost:8000", description="URL пользовательского сервиса")
    ORDER_SERVICE_URL: str = Field(default="http://localhost:8001", description="URL сервиса проектов")
    SERVICE_SERVICE_URL: str    = Field(default="http://localhost:8002", description="URL сервиса задач")

    # Настройки базы данных
    DATABASE_URL: str = Field(..., description="URL базы данных")

    # Настройки безопасности
    SECRET_KEY: str = Field(..., description="Секретный ключ приложения")

    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_SERVICE_TOPIC: str
    KAFKA_CONSUMER_GROUP: str
    KAFKA_MAX_RETRIES: int = 3
    KAFKA_RETRY_DELAY: int = 1

    @validator("MONGODB_URL")
    def validate_mongodb_url(cls, value: str) -> str:
        if not value.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("Invalid MongoDB URL format")
        return value

    @validator("USER_SERVICE_URL", "order_SERVICE_URL", "service_SERVICE_URL")
    def validate_service_urls(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("Invalid service URL format")
        return value

    class Config:
        env_file = ".env"
        case_sensitive = False   # Игнорировать регистр в именах переменных
        populate_by_name = True  # Поддержка заполнения через Field(name="...")

# Создаем экземпляр настроек
settings = Settings()

# Экспортируем значения для удобства импорта в других частях приложения
MONGODB_URL         = settings.MONGODB_URL
MONGODB_DB_NAME     = settings.MONGODB_DB_NAME
USER_SERVICE_URL    = settings.USER_SERVICE_URL
ORDER_SERVICE_URL = settings.ORDER_SERVICE_URL
SERVICE_SERVICE_URL    = settings.SERVICE_SERVICE_URL

# order-management-system/services/service_service/src/api/routes.py

# Импорты библиотек
from typing import List, Optional, AsyncGenerator
from uuid import UUID

# Импорты FastAPI
from fastapi import APIRouter, Depends, HTTPException, Query, status

# Логирование
import logging

# Локальные импорты
from ..services.command_service import ServiceCommandService
from ..services.query_service import ServiceQueryService
from ..services.service_service import ServiceService
from ..models.api_models import ServiceCreate, ServiceUpdate, ServiceResponse
from ..models.mongo_models import ServiceStatus, ServicePriority
from ..auth import get_current_user, User
from ..database import MongoDBManager

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Маршрутизатор FastAPI
router = APIRouter(prefix="/services", tags=["services"])


# Dependency Injection функции
async def get_service_command_service() -> AsyncGenerator[ServiceCommandService, None]:
    kafka_producer = None
    try:
        # Инициализация Kafka producer
        kafka_producer = KafkaServiceProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            topic=settings.KAFKA_SERVICE_TOPIC
        )
        await kafka_producer.start()
        
        # Создание command service
        command_service = ServiceCommandService(kafka_producer)
        yield command_service
    except Exception as e:
        logger.error(f"Failed to initialize command service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize command service"
        )
    finally:
        if kafka_producer:
            await kafka_producer.stop()

async def get_service_query_service() -> AsyncGenerator[ServiceQueryService, None]:
    db_manager = None
    try:
        # Инициализация MongoDB manager
        db_manager = MongoDBManager()
        await db_manager.connect()
        
        # Создание query service
        query_service = ServiceQueryService(db_manager)
        yield query_service
    except Exception as e:
        logger.error(f"Failed to initialize query service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize query service"
        )
    finally:
        if db_manager:
            await db_manager.disconnect()

# Dependency для получения экземпляра serviceService
async def get_service_service() -> AsyncGenerator[ServiceService, None]:
    db_manager = None
    try:
        # Создаем экземпляр и сохраняем его
        db_manager = MongoDBManager()
        # Подключаемся и сохраняем результат
        connected_manager = await db_manager.connect()
        logger.info("Подключение к MongoDB успешно")

        service = ServiceService(connected_manager)
        logger.info("serviceService успешно инициализирован")

        yield service

    except Exception as e:
        logger.error(f"Не удалось инициализировать serviceService: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка инициализации сервиса задач."
        )

    finally:
        if db_manager:
            logger.info("Закрытие подключения к MongoDB")
            await db_manager.disconnect()
            logger.info("Подключение к MongoDB закрыто")

@router.post("", response_model=ServiceResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_service(
    service: ServiceCreate,
    current_user: User = Depends(get_current_user),
    command_service: ServiceCommandService = Depends(get_service_command_service)
) -> ServiceResponse:
    try:
        service_dict = await command_service.create_service(service, current_user.id)
        return ServiceResponse(**service_dict)
    except Exception as e:
        logger.error(f"Error creating service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating service: {str(e)}"
        )

@router.get("", response_model=List[ServiceResponse])
async def get_services(
    order_id: Optional[UUID] = None,
    assignee_id: Optional[UUID] = None,
    status: Optional[ServiceStatus] = None,
    priority: Optional[ServicePriority] = None,
    current_user: User = Depends(get_current_user),
    query_service: ServiceQueryService = Depends(get_service_query_service)
) -> List[ServiceResponse]:
    try:
        criteria = {
            k: v for k, v in {
                "order_id": order_id,
                "assignee_id": assignee_id,
                "status": status,
                "priority": priority
            }.items() if v is not None
        }
        services = await query_service.get_services_by_criteria(criteria)
        return [ServiceResponse.from_mongo(service) for service in services]
    except Exception as e:
        logger.error(f"Error fetching services: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching services: {str(e)}"
        )


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: UUID,
    current_user: User = Depends(get_current_user),
    service_service: ServiceService = Depends(get_service_service)
) -> ServiceResponse:
    try:
        service = await service_service.get_service(service_id)
        if service is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"service {service_id} not found"
            )
        return ServiceResponse.from_mongo(service)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching service {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching service: {str(e)}"
        )

@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    service_update: ServiceUpdate,
    current_user: User = Depends(get_current_user),
    service_service: ServiceService = Depends(get_service_service)
) -> ServiceResponse:
    try:
        # Проверяем существование задачи
        existing_service = await service_service.get_service(service_id)
        if existing_service is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"service {service_id} not found"
            )

        # Проверяем права доступа
        if (existing_service.creator_id != current_user.id and 
            existing_service.assignee_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this service"
            )

        logger.info(f"Updating service {service_id} by user {current_user.id}")
        updated_service = await service_service.update_service(service_id, service_update)
        if updated_service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update service"
            )
        logger.info(f"service {service_id} updated successfully")
        return ServiceResponse.from_mongo(updated_service)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating service: {str(e)}"
        )

@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: UUID,
    current_user: User = Depends(get_current_user),
    service_service: ServiceService = Depends(get_service_service)
):
    try:
        # Проверяем существование задачи
        existing_service = await service_service.get_service(service_id)
        if existing_service is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"service {service_id} not found"
            )

        # Проверяем права доступа
        if existing_service.creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this service"
            )

        logger.info(f"Deleting service {service_id} by user {current_user.id}")
        success = await service_service.delete_service(service_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete service"
            )
        logger.info(f"service {service_id} deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting service {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting service: {str(e)}"
        )

@router.patch("/{service_id}/status", response_model=ServiceResponse)
async def update_service_status(
    service_id: UUID,
    status: ServiceStatus,
    current_user: User = Depends(get_current_user),
    service_service: ServiceService = Depends(get_service_service)
) -> ServiceResponse:
    try:
        # Проверяем существование задачи
        existing_service = await service_service.get_service(service_id)
        if existing_service is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"service {service_id} not found"
            )

        # Проверяем права доступа
        if (existing_service.creator_id != current_user.id and 
            existing_service.assignee_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this service status"
            )

        logger.info(f"Updating status of service {service_id} to {status} by user {current_user.id}")
        service_update = ServiceUpdate(status=status)
        updated_service = await service_service.update_service(service_id, service_update)
        if updated_service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update service status"
            )
        logger.info(f"service {service_id} status updated successfully")
        return ServiceResponse.from_mongo(updated_service)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service status {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating service status: {str(e)}"
        )

@router.patch("/{service_id}/assignee", response_model=ServiceResponse)
async def update_service_assignee(
    service_id: UUID,
    assignee_id: Optional[UUID],
    current_user: User = Depends(get_current_user),
    service_service: ServiceService = Depends(get_service_service)
) -> ServiceResponse:
    try:
        # Проверяем существование задачи
        existing_service = await service_service.get_service(service_id)
        if existing_service is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"service {service_id} not found"
            )

        # Проверяем права доступа
        if existing_service.creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update service assignee"
            )

        logger.info(f"Updating assignee of service {service_id} to {assignee_id} by user {current_user.id}")
        service_update = ServiceUpdate(assignee_id=assignee_id)
        updated_service = await service_service.update_service(service_id, service_update)
        if updated_service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update service assignee"
            )
        logger.info(f"service {service_id} assignee updated successfully")
        return ServiceResponse.from_mongo(updated_service)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service assignee {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating service assignee: {str(e)}"
        )