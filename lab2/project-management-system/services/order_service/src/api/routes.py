# order-management-system/services/order_service/src/api/routes.py
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

# Импорт моделей
from ..models.database_models import Order as OrderDB
from ..models.api_models import (
    OrderCreate,
    Order as OrderResponse
)
from ..database import db
from ..auth import get_current_user, User

router = APIRouter()

@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate, current_user: User = Depends(get_current_user)) -> OrderResponse:
    """
    Description:
        Создание нового проекта.

    Args:
        order (orderCreate): Данные проекта для создания.
        current_user (User): Аутентифицированный пользователь.

    Returns:
        orderResponse: Данные созданного проекта.

    Raises:
        HTTPException: При ошибках создания проекта.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    order_data = {**order.dict(), "owner_id": current_user.id}

    try:
        return db.create(OrderDB, order_data)
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating order"
        )

@router.get("/orders", response_model=List[OrderResponse])
async def read_orders(current_user: User = Depends(get_current_user)) -> List[OrderResponse]:
    """
    Description:
        Получение списка проектов текущего пользователя.

    Args:
        current_user (User): Аутентифицированный пользователь.

    Returns:
        List[orderResponse]: Список проектов пользователя.

    Raises:
        HTTPException: При ошибках получения проектов.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        orders = db.get_multi(OrderDB)
        return [p for p in orders if p.owner_id == current_user.id]
    except Exception as e:
        print(f"Error getting orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving orders"
        )

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def read_order(order_id: UUID, current_user: User = Depends(get_current_user)) -> OrderResponse:
    """
    Description:
        Получение информации о конкретном проекте.

    Args:
        order_id (UUID): Идентификатор проекта.
        current_user (User): Аутентифицированный пользователь.

    Returns:
        orderResponse: Данные проекта.

    Raises:
        HTTPException: При ошибках получения проекта.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        order = db.get(OrderDB, order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="order not found"
            )
        if order.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        return order
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving order"
        )

@router.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: UUID,
    order: OrderCreate,
    current_user: User = Depends(get_current_user)
) -> OrderResponse:
    """
    Description:
        Обновление информации о проекте.

    Args:
        order_id (UUID): Идентификатор проекта.
        order (orderCreate): Данные для обновления проекта.
        current_user (User): Аутентифицированный пользователь.

    Returns:
        orderResponse: Обновленные данные проекта.

    Raises:
        HTTPException: При ошибках обновления проекта.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        existing_order = db.get(OrderDB, order_id)
        if not existing_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="order not found"
            )
        if existing_order.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )

        update_data = order.dict(exclude_unset=True)
        return db.update(OrderDB, order_id, update_data)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating order"
        )

@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(order_id: UUID, current_user: User = Depends(get_current_user)) -> None:
    """
    Description:
        Удаление проекта.

    Args:
        order_id (UUID): Идентификатор проекта.
        current_user (User): Аутентифицированный пользователь.

    Returns:
        None

    Raises:
        HTTPException: При ошибках удаления проекта.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        existing_order = db.get(OrderDB, order_id)
        if not existing_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="order not found"
            )
        if existing_order.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )

        db.delete(OrderDB, order_id)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting order"
        )