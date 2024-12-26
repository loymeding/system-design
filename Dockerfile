# Используем базовый образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

# Запускаем скрипты инициализации и приложение
CMD ["sh", "-c", "python init_db_mongo.py && python init_db_pg.py && uvicorn profi_service_jwt:app --host 0.0.0.0 --port 8000"]
