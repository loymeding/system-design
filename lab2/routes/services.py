from fastapi import APIRouter, Depends, status
from auth import get_current_user
from database import services_db
from models import ServiceOrder, CreateServiceOrder
from datetime import datetime

router = APIRouter()


@router.get("/", response_model=list[ServiceOrder])
def list_services(current_user: dict = Depends(get_current_user)):
    return services_db


@router.post("/", response_model=ServiceOrder, status_code=status.HTTP_201_CREATED)
def create_service_order(order: CreateServiceOrder, current_user: dict = Depends(get_current_user)):
    service_order = ServiceOrder(
        id=len(services_db) + 1,
        user=current_user["username"],
        service_name=order.service_name,
        details=order.details,
        created_at=datetime.utcnow()
    )
    services_db.append(service_order)
    return service_order
