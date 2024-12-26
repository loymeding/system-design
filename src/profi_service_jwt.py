from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from pymongo import MongoClient
import threading
import json

# Импорт Producer
from confluent_kafka import Producer

# Импорт модулей
from kafka_service import get_kafka_producer, kafka_consumer_service
from models import UserMongo, Service, Order, ServiceDB, OrderDB
from dependencies import get_db, get_current_client, SessionLocal
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, MONGO_URI, KAFKA_TOPIC

# Инициализация FastAPI
app = FastAPI()

# Настройка MongoDB
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["carpooling"]
mongo_users_collection = mongo_db["users"]

# Настройка паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Настройка OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# JWT функции
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Маршруты API
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = mongo_users_collection.find_one({"username": form_data.username})
    if user and pwd_context.verify(form_data.password, user["hashed_password"]):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.post("/users", response_model=UserMongo)
def create_user(user: UserMongo, current_user: str = Depends(get_current_client)):
    user_dict = user.dict()
    user_dict["hashed_password"] = pwd_context.hash(user_dict["hashed_password"])
    user_id = mongo_users_collection.insert_one(user_dict).inserted_id
    user_dict["id"] = str(user_id)
    return user_dict


@app.post("/services", response_model=Service)
def create_service(service: Service, producer: Producer = Depends(get_kafka_producer),
                   current_user: str = Depends(get_current_client)):
    producer.produce(KAFKA_TOPIC, key=str(service.user_id), value=json.dumps(service.dict()).encode("utf-8"))
    producer.flush()
    return service


@app.post("/orders/{user_id}", response_model=Order)
def add_services_to_order(user_id: int, service_ids: List[int], db: Session = Depends(get_db)):
    # Проверка наличия услуг в базе
    services = db.query(ServiceDB).filter(ServiceDB.id.in_(service_ids)).all()
    if not services:
        raise HTTPException(status_code=404, detail="Services not found")

    # Создание заказа
    total_cost = sum(service.cost for service in services)
    order = OrderDB(user_id=user_id, services_id=service_ids, cost=total_cost, date=datetime.utcnow())
    db.add(order)
    db.commit()
    db.refresh(order)
    return Order(id=order.id, user_id=order.user_id, services_id=order.services_id, cost=order.cost, date=order.date)


@app.get("/orders/{user_id}", response_model=List[Order])
def get_user_orders(user_id: int, db: Session = Depends(get_db)):
    orders = db.query(OrderDB).filter(OrderDB.user_id == user_id).all()
    if not orders:
        raise HTTPException(status_code=404, detail="Orders not found")

    return [
        Order(
            id=order.id,
            user_id=order.user_id,
            services_id=order.services_id or [],
            cost=order.cost,
            date=order.date
        )
        for order in orders
    ]


# Запуск Kafka Consumer в фоновом режиме
def start_kafka_consumer():
    thread = threading.Thread(target=kafka_consumer_service, daemon=True)
    thread.start()


start_kafka_consumer()

# Запуск сервера
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
