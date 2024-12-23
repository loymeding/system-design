# order-management-system/services/service_service/src/services/query_service.py

# Стандартные библиотеки
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

# Локальные импорты
from ..database import MongoDBManager
from ..models.mongo_models import MongoService

# Настройка логирования
logger = logging.getLogger(__name__)


class ServiceQueryService:
    """
    Description:
        Сервис для выполнения запросов к задачам в MongoDB.

    Args:
        db_manager: Менеджер базы данных MongoDB

    Examples:
        >>> service = serviceQueryService(db_manager)
        >>> service = await service.get_service(service_id)
    """

    def __init__(self, db_manager: MongoDBManager) -> None:
        self.db: MongoDBManager = db_manager

    async def get_service(self, service_id: UUID) -> Optional[MongoService]:
        """
        Description:
            Получает задачу по идентификатору.

        Args:
            service_id: Идентификатор задачи

        Returns:
            Optional[Mongoservice]: Найденная задача или None

        Raises:
            Exception: При ошибке получения задачи

        Examples:
            >>> service = await service.get_service(UUID("123..."))
        """
        try:
            return await self.db.get_service(service_id)
        except Exception as e:
            logger.error(f"Error in get_service query: {str(e)}")
            raise

    async def get_services_by_criteria(
        self,
        criteria: Dict[str, Any]
    ) -> List[MongoService]:
        """
        Description:
            Получает список задач по заданным критериям.

        Args:
            criteria: Словарь критериев фильтрации

        Returns:
            List[Mongoservice]: Список найденных задач

        Raises:
            Exception: При ошибке получения задач

        Examples:
            >>> services = await service.get_services_by_criteria({
            ...     "status": "IN_PROGRESS"
            ... })
        """
        try:
            return await self.db.get_services_by_criteria(criteria)
        except Exception as e:
            logger.error(f"Error in get_services_by_criteria query: {str(e)}")
            raise