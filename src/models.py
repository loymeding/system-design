from pydantic import BaseModel
from typing import List
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class UserMongo(BaseModel):
    id: str
    username: str
    first_name: str
    last_name: str
    hashed_password: str
    email: str


class Service(BaseModel):
    id: int
    user_id: int
    description: str
    cost: int


class Order(BaseModel):
    id: int
    user_id: int
    services_id: List[int] = []
    cost: int = 0
    date: datetime


class ServiceDB(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    description = Column(String, index=False)
    cost = Column(Integer, index=False)


class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    services_id = Column(ARRAY(Integer), index=False)
    cost = Column(Integer, index=False)
    date = Column(DateTime, index=True)