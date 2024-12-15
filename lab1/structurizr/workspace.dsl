workspace {
    model {
        user = Person "Пользователь" "Оформляет заявки на услуги и отслеживает их статус"
        contractor = Person "Исполнитель" "Получает и выполняет заявки пользователей"
        system = SoftwareSystem "Сайт заказа услуг" "Позволяет пользователям создавать заявки и исполнителям их принимать" {
            frontend = Container "Frontend" "Пользовательский интерфейс" "React.js"
            backend = Container "Backend" "Бизнес-логика и API" "Node.js"
            database = Container "Database" "Хранение данных" "PostgreSQL"

            user -> frontend "Работает с интерфейсом"
            contractor -> frontend "Работает с интерфейсом"
            frontend -> backend "Отправляет запросы"
            backend -> database "Читает и записывает данные"
            backend -> frontend "Возвращает ответы"
        }
    }

    views {
        systemContext system {
            include *
            autolayout lr
        }

        container system {
            include *
            autolayout lr
        }

        dynamic system {
            title "Создание заказа"
            user -> frontend "Создает заявку"
            frontend -> backend "Отправляет данные заявки"
            backend -> database "Сохраняет данные заявки"
            backend -> frontend "Подтверждает сохранение"
        }
    }
}
