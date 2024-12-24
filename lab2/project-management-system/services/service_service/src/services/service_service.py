# order-management-system/services/service_service/src/services/service_service.py
# Импорт стандартных библиотек
import logging
from uuid import UUID
from typing import List, Optional, Dict, Any

# order imports
from ..models.mongo_models import MongoService
from ..models.api_models import ServiceCreate, ServiceUpdate

# Настройка логирования
logger = logging.getLogger(__name__)

class ServiceService:
    """
    Description:
        Сервис для управления задачами в проекте.
    """
    
    def __init__(self, db_manager):
        """
        Description:
            Инициализация ServiceService с менеджером базы данных.

        Args:
            db_manager: Менеджер для взаимодействия с базой данных.
        """
        self.db = db_manager

    async def create_service(self, service_data: ServiceCreate, creator_id: UUID) -> MongoService:
        """
        Description:
            Создает новую задачу и сохраняет её в базе данных.

        Args:
            service_data: Данные для создания задачи.
            creator_id: Идентификатор пользователя, создающего задачу.

        Returns:
            Созданная задача в формате Mongoservice.

        Raises:
            Exception: В случае ошибки сохранения задачи.

        Examples:
            >>> await create_service(service_data, UUID("123e4567-e89b-12d3-a456-426614174000"))
        """
        try:
            logger.info("Начало создания задачи в ServiceService")
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
            logger.debug(f"Создан объект MongoService: {service.model_dump_json(indent=2)}")

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

    async def update_service(self, service_id: UUID, service_update: ServiceUpdate) -> Optional[MongoService]:
        """
        Description:
            Обновляет данные задачи.

        Args:
            service_id: Идентификатор задачи.
            service_update: Данные для обновления задачи.

        Returns:
            Обновлённая задача или None, если задача не найдена.

        Examples:
            >>> await update_service(UUID("123e4567-e89b-12d3-a456-426614174000"), service_update)
        """
        try:
            update_data = service_update.dict(exclude_unset=True)
            updated_service = await self.db.update_service(service_id, update_data)
            logger.info(f"Задача {service_id} успешно обновлена.")
            return updated_service
        except Exception as e:
            logger.error(f"Ошибка обновления задачи: {str(e)}")
            raise

    async def delete_service(self, service_id: UUID) -> bool:
        """
        Description:
            Удаляет задачу из базы данных.

        Args:
            service_id: Идентификатор задачи.

        Returns:
            True, если задача успешно удалена, иначе False.

        Examples:
            >>> await delete_service(UUID("123e4567-e89b-12d3-a456-426614174000"))
        """
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


    async def get_services_by_criteria(self, criteria: Dict[str, Any]) -> List[MongoService]:
        """
        Description:
            Получает задачи, соответствующие заданным критериям.

        Args:
            criteria: Словарь с критериями фильтрации задач.

        Returns:
            Список задач, соответствующих критериям.

        Examples:
            >>> await get_services_by_criteria({"priority": "high"})
        """
        try:
            services = await self.db.get_services_by_criteria(criteria)
            logger.info(f"Найдено {len(services)} задач по критериям {criteria}.")
            return services
        except Exception as e:
            logger.error(f"Ошибка получения задач по критериям: {str(e)}")
            raise
