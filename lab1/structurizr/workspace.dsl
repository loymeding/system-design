workspace {
    model {
        user = person "Пользователь" "Человек, который заказывает услуги через систему."
        service_provider = person "Исполнитель" "Человек, который предоставляет услуги."

        system = softwareSystem "Сайт заказа услуг" "Онлайн-платформа для поиска и заказа услуг." {
            webapp = container "Веб-приложение" "Позволяет пользователям искать и заказывать услуги." "Python (Flask/Django)"
            backend = container "Серверная часть" "Обрабатывает запросы, управляет логикой." "Python (FastAPI)"
            database = container "База данных" "Хранит данные о пользователях, услугах и заказах." "PostgreSQL"
        }

        user -> system "Ищет и заказывает услуги"
        service_provider -> system "Добавляет услуги и управляет заказами"

        user -> webapp "Взаимодействует через интерфейс"
        service_provider -> webapp "Управляет своими услугами"
        webapp -> backend "Передает запросы"
        backend -> database "Читает и записывает данные"
        database -> backend "Возвращает данные"
        backend -> webapp "Отправляет результаты запросов"
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

        dynamic system "poisk_uslugi" { 
            user -> webapp "Вводит параметры поиска"
            webapp -> backend "Передает запрос на поиск"
            backend -> database "Запрашивает данные"
            database -> backend "Возвращает результаты поиска"
            backend -> webapp "Передает результаты поиска"
            webapp -> user "Отображает список услуг"
        }
    }
}
