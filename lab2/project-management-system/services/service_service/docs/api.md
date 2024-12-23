# API Reference

## POST /services

**Description:** Создание новой задачи.

**Request Body:**
```json
{
    "title": "string",         // 1-200 символов
    "description": "string",   // до 2000 символов
    "priority": "low|medium|high",
    "order_id": "uuid",
    "assignee_id": "uuid"      // опционально
}
```

**Response:**
```json
{
    "id": "uuid",
    "title": "string",
    "description": "string",
    "priority": "string",
    "status": "created",
    "order_id": "uuid",
    "creator_id": "uuid",
    "assignee_id": "uuid",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

## GET /services

**Description:** Получение списка задач.

**Query Parameters:**
- `order_id`: `uuid` (опционально)
- `assignee_id`: `uuid` (опционально)
- `status`: `created|in_progress|on_review|completed` (опционально)
- `priority`: `low|medium|high` (опционально)

**Response:**
```json
[
    {
        "id": "uuid",
        "title": "string",
        "description": "string",
        "priority": "string",
        "status": "string",
        "order_id": "uuid",
        "creator_id": "uuid",
        "assignee_id": "uuid",
        "created_at": "datetime",
        "updated_at": "datetime"
    },
    // Другие задачи
]
```

## GET /services/{service_id}

**Description:** Получение задачи по ID.

**Path Parameters:**
- `service_id`: `uuid`

**Response:**
```json
{
    "id": "uuid",
    "title": "string",
    "description": "string",
    "priority": "string",
    "status": "string",
    "order_id": "uuid",
    "creator_id": "uuid",
    "assignee_id": "uuid",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

## PUT /services/{service_id}

**Description:** Обновление задачи.

**Path Parameters:**
- `service_id`: `uuid`

**Request Body:**
```json
{
    "title": "string",         // опционально
    "description": "string",   // опционально
    "status": "string",        // опционально
    "priority": "string",      // опционально
    "assignee_id": "uuid"      // опционально
}
```

**Response:**
```json
{
    "id": "uuid",
    "title": "string",
    "description": "string",
    "priority": "string",
    "status": "string",
    "order_id": "uuid",
    "creator_id": "uuid",
    "assignee_id": "uuid",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

## DELETE /services/{service_id}

**Description:** Удаление задачи.

**Path Parameters:**
- `service_id`: `uuid`

**Response:**
```
204 No Content
```

## PATCH /services/{service_id}/status

**Description:** Обновление статуса задачи.

**Path Parameters:**
- `service_id`: `uuid`

**Request Body:**
```json
{
    "status": "created|in_progress|on_review|completed"
}
```

**Response:**
```json
{
    "id": "uuid",
    "title": "string",
    "description": "string",
    "priority": "string",
    "status": "string",
    "order_id": "uuid",
    "creator_id": "uuid",
    "assignee_id": "uuid",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

## PATCH /services/{service_id}/assignee

**Description:** Обновление исполнителя задачи.

**Path Parameters:**
- `service_id`: `uuid`

**Request Body:**
```json
{
    "assignee_id": "uuid"
}
```

**Response:**
```json
{
    "id": "uuid",
    "title": "string",
    "description": "string",
    "priority": "string",
    "status": "string",
    "order_id": "uuid",
    "creator_id": "uuid",
    "assignee_id": "uuid",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

## GET /health

**Description:** Проверка работоспособности сервиса.

**Response:**
```json
{
    "status": "healthy"
}
```

## Authentication

Все эндпоинты требуют JWT-токена для аутентификации. Токен должен быть передан в заголовке `Authorization` в формате `Bearer <token>`.

## Error Handling

- **401 Unauthorized:** Отсутствует токен аутентификации.
- **403 Forbidden:** Нет прав для выполнения операции.
- **404 Not Found:** Задача не найдена.
- **500 Internal Server Error:** Внутренняя ошибка сервера.

## Data Types

- `uuid`: Уникальный идентификатор в формате UUID.
- `datetime`: Дата и время в формате ISO 8601.

## Notes

- Поля `created_at` и `updated_at` автоматически генерируются системой.
- Поля `status` и `priority` имеют фиксированные значения, которые должны соответствовать указанным enum-значениям.