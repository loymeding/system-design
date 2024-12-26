import datetime
import time
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, ServiceDB, OrderDB

# Получаем текущую директорию
current_dir = os.getcwd()

# Определяем директорию на один уровень выше
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Настройка PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:archdb@db/carpooling"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание таблиц
Base.metadata.create_all(bind=engine)


# Загрузка тестовых данных
def load_test_data():
    db = SessionLocal()

    # Проверка существования услуги перед добавлением
    def add_service(description, cost, user_id):
        if not isinstance(cost, int):  # Проверка типа
            raise ValueError("Cost must be an integer.")
        service = db.query(ServiceDB).filter(ServiceDB.description == description, ServiceDB.cost == cost, ServiceDB.user_id == user_id).first()
        if not service:
            service = ServiceDB(
                description=description,
                user_id=user_id,
                cost=cost
            )
            db.add(service)

    # Проверка существования заказа перед добавлением
    def add_order(user_id, services_id=None):
        if not services_id:
            services_id = []
        total_cost = 0
        if services_id:
            # Проверяем, существуют ли услуги с указанными ID
            services = db.query(ServiceDB).filter(ServiceDB.id.in_(services_id)).all()
            if not services:
                raise ValueError("One or more service IDs do not exist.")

            # Суммируем стоимость всех услуг
            total_cost = sum(service.cost for service in services)

        # Добавляем заказ
        order = OrderDB(
            user_id=user_id,
            services_id=services_id,
            cost=total_cost,
            date=datetime.datetime.now()
        )
        db.add(order)

    # Создание тестовых услуг
    add_service(description='Мойка полов', user_id=1, cost=1500)
    add_service(description='Вынос мусора', user_id=1, cost=500)

    # Создание тестовых заказов
    add_order(user_id=1)
    add_order(user_id=2)

    db.commit()
    db.close()


def wait_for_db(retries=10, delay=5):
    for _ in range(retries):
        try:
            engine.connect()
            print("PostgreSQL is ready!")
            return
        except Exception as e:
            print(f"PostgreSQL not ready yet: {e}")
            time.sleep(delay)
    raise Exception("Could not connect to PostgreSQL")


if __name__ == "__main__":
    wait_for_db()
    load_test_data()
