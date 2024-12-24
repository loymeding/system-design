# order-management-system/services/service_service/src/api/routes.py

# Стандартные библиотеки
import logging
from typing import List, Optional, AsyncGenerator
from uuid import UUID

# Сторонние библиотеки
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

# Локальные импорты
from ..auth import get_current_user, User
from ..core.config import Settings
from ..database import MongoDBManager
from ..events.kafka_producer import KafkaServiceProducer
from ..models.api_models import (
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
)
from ..models.mongo_models import (
    ServiceStatus,
    ServicePriority,
)
from ..services.command_service import ServiceCommandService
from ..services.query_service import ServiceQueryService
from ..services.service_service import ServiceService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание маршрутизатора FastAPI
router = APIRouter(prefix="/services", tags=["services"])


async def get_service_command_service() -> AsyncGenerator[ServiceCommandService, None]:
    """
    Description:
        Dependency injection для сервиса команд задач.
        Инициализирует Kafka producer и создает command service.

    Returns:
        AsyncGenerator[serviceCommandService, None]: Генератор сервиса команд

    Raises:
        HTTPException: При ошибке инициализации сервиса

    Examples:
        >>> service = await anext(get_service_command_service())
    """
    kafka_producer = None
    try:
        kafka_producer = KafkaServiceProducer(
            bootstrap_servers=Settings.KAFKA_BOOTSTRAP_SERVERS,
            topic=Settings.KAFKA_SERVICE_TOPIC
        )
        await kafka_producer.start()
        
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
    """
    Description:
        Dependency injection для сервиса запросов задач.
        Инициализирует MongoDB manager и создает query service.

    Returns:
        AsyncGenerator[serviceQueryService, None]: Генератор сервиса запросов

    Raises:
        HTTPException: При ошибке инициализации сервиса

    Examples:
        >>> service = await anext(get_service_query_service())
    """
    db_manager = None
    try:
        db_manager = MongoDBManager()
        await db_manager.connect()
        
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
    """
    Description:
        Dependency для внедрения serviceService.

    Returns:
        Экземпляр serviceService.

    Raises:
        HTTPException: В случае ошибок подключения к MongoDB.

    Examples:
        Используется в маршрутах FastAPI:
        >>> @router.get("/")
        >>> async def get_services(service: ServiceService = Depends(get_service_service)):
        >>>     return await service.get_services()
    """
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
    """
    Description:
        Создает новую задачу в системе.

    Args:
        service: Данные для создания задачи
        current_user: Текущий пользователь
        command_service: Сервис для обработки команд

    Returns:
        serviceResponse: Созданная задача

    Raises:
        HTTPException: При ошибке создания задачи

    Examples:
        >>> response = await create_service(
        ...     service=ServiceCreate(title="New service"),
        ...     current_user=current_user,
        ...     command_service=command_service
        ... )
    """
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
    cost: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    query_service: ServiceQueryService = Depends(get_service_query_service)
) -> List[ServiceResponse]:
    """
    Description:
        Получает список задач с возможностью фильтрации.

    Args:
        order_id: ID проекта для фильтрации
        assignee_id: ID исполнителя для фильтрации
        status: Статус задачи для фильтрации
        priority: Приоритет задачи для фильтрации
        current_user: Текущий пользователь
        query_service: Сервис для выполнения запросов

    Returns:
        List[serviceResponse]: Список задач

    Raises:
        HTTPException: При ошибке получения задач

    Examples:
        >>> services = await get_services(
        ...     order_id=UUID("..."),
        ...     status=ServiceStatus.IN_PROGRESS
        ... )
    """
    try:
        criteria = {
            k: v for k, v in {
                "order_id": order_id,
                "assignee_id": assignee_id,
                "cost": cost
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
    """
    Description:
        Получение задачи по ID.

    Args:
        service_id (UUID): ID задачи
        current_user (User): Текущий пользователь
        service_service (serviceService): Сервис для работы с задачами

    Returns:
        serviceResponse: Задача

    Raises:
        HTTPException: Если задача не найдена
    """
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
    """
    Description:
        Обновление задачи.

    Args:
        service_id (UUID): ID задачи
        service_update (serviceUpdate): Данные для обновления
        current_user (User): Текущий пользователь
        service_service (serviceService): Сервис для работы с задачами

    Returns:
        serviceResponse: Обновленная задача

    Raises:
        HTTPException: Если задача не найдена или произошла ошибка обновления
    """
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
    """
    Description:
        Удаление задачи.

    Args:
        service_id (UUID): ID задачи
        current_user (User): Текущий пользователь
        service_service (serviceService): Сервис для работы с задачами

    Raises:
        HTTPException: Если задача не найдена или нет прав на удаление
    """
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


@router.patch("/{service_id}/assignee", response_model=ServiceResponse)
async def update_service_assignee(
    service_id: UUID,
    assignee_id: Optional[UUID],
    current_user: User = Depends(get_current_user),
    service_service: ServiceService = Depends(get_service_service)
) -> ServiceResponse:
    """
    Description:
        Обновление исполнителя задачи.

    Args:
        service_id (UUID): ID задачи
        assignee_id (UUID, optional): ID нового исполнителя
        current_user (User): Текущий пользователь
        service_service (serviceService): Сервис для работы с задачами

    Returns:
        serviceResponse: Обновленная задача

    Raises:
        HTTPException: При ошибке обновления исполнителя
    """
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