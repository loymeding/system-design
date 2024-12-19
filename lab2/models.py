from pydantic import BaseModel
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class ServiceOrder(BaseModel):
    id: int
    user: str
    service_name: str
    details: str
    created_at: datetime


class CreateServiceOrder(BaseModel):
    service_name: str
    details: str
