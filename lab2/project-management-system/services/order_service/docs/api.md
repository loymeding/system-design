## API Reference

### POST /orders
Создание нового проекта
```json
Request:
{
    "name": "string",         // 1-100 символов
    "description": "string"   // до 1000 символов
}

Response:
{
    "id": "uuid",
    "name": "string",
    "description": "string",
    "owner_id": "uuid",
    "created_at": "datetime",
    "updated_at": "datetime",
    "service_count": "number"    // опционально
}
```

### GET /orders
Получение списка проектов пользователя
```json
Response: Array[order]
```

### GET /orders/{order_id}
Получение проекта по ID
```json
Response: order
```

### PUT /orders/{order_id}
Обновление проекта
```json
Request:
{
    "name": "string",         // опционально
    "description": "string"   // опционально
}

Response: order
```

### DELETE /orders/{order_id}
Удаление проекта
```
Response: 204 No Content
```

### GET /orders/search
Поиск проектов
```
Query Parameters:
- name: string (поисковый запрос)

Response: Array[order]
```

## Примеры использования API

### Создание проекта
```python
import requests

# Создание проекта
response = requests.post(
    "http://localhost:8001/orders",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "name": "New order",
        "description": "order description"
    }
)
order = response.json()
```

### Поиск проектов
```python
# Поиск проектов по имени
response = requests.get(
    "http://localhost:8001/orders/search",
    headers={"Authorization": f"Bearer {token}"},
    params={"name": "order"}
)
orders = response.json()
```

### Обновление проекта
```python
# Обновление проекта
response = requests.put(
    f"http://localhost:8001/orders/{order_id}",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "name": "Updated order",
        "description": "New description"
    }
)
updated_order = response.json()
```