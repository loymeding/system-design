workspace {
    model {
        user = person "Пользователь" "Человек, который заказывает услуги через систему."
        service_provider = person "Исполнитель" "Человек, который предоставляет услуги."

        web_application = softwareSystem "Веб-приложение" "Позволяет пользователям и исполнителям взаимодействовать с системой." {
            web_ui = container "Веб-интерфейс" "Обеспечивает интерфейс для взаимодействия пользователей и исполнителей с системой." "HTML, CSS, JavaScript"
            web_backend = container "Серверная часть веб-приложения" "Обрабатывает запросы от веб-интерфейса и взаимодействует с API других сервисов." "Python (FastAPI)"
        }

        users_service = softwareSystem "Сервис пользователей" "Управляет данными пользователей и их аутентификацией." {
            users_api = container "API пользователей" "Обеспечивает функционал аутентификации и управления пользователями." "Python (FastAPI)"
            users_database = container "База данных пользователей" "Хранит данные о пользователях." "PostgreSQL"
        }

        services_service = softwareSystem "Сервис услуг" "Управляет данными об услугах." {
            services_api = container "API услуг" "Обеспечивает функционал управления услугами." "Python (FastAPI)"
            services_database = container "База данных услуг" "Хранит данные об услугах." "PostgreSQL"
        }

        orders_service = softwareSystem "Сервис заказов" "Управляет созданием и обработкой заказов." {
            orders_api = container "API заказов" "Обеспечивает функционал создания и управления заказами." "Python (FastAPI)"
            orders_database = container "База данных заказов" "Хранит данные о заказах." "PostgreSQL"
        }

 
        user -> web_ui "Ищет и заказывает услуги"
        service_provider -> web_ui "Добавляет услуги и управляет заказами"
        web_ui -> web_backend "Передает запросы"
        
        web_backend -> users_api "Передает запросы на исполнение"
        web_backend -> services_api "Передает запросы на исполнение"
        web_backend -> orders_api "Передает запросы на исполнение"
    
        users_api -> users_database "Читает и записывает данные о пользователях"
        services_api -> services_database "Читает и записывает данные об услугах"
        orders_api -> orders_database "Читает и записывает данные о заказах"

        users_database -> users_api "Возвращает данные о пользователях"
        services_database -> services_api "Возвращает данные об услугах"
        orders_database -> orders_api "Возвращает данные о заказах"

        users_api -> web_backend "Отправляет результаты запросов"
        services_api  -> web_backend "Отправляет результаты запросов"
        orders_api -> web_backend "Отправляет результаты запросов" 

        web_backend -> web_ui "Отправляет результаты запросов для отображения"
    }

    views {
        systemContext web_application {
            include *
            autolayout lr
        }

        systemContext users_service {
            include *
            autolayout lr
        }

        systemContext services_service {
            include *
            autolayout lr
        }

        systemContext orders_service {
            include *
            autolayout lr
        }

        container web_application {
            include *
            autolayout lr
        }

        container users_service {
            include *
            autolayout lr
        }

        container services_service {
            include *
            autolayout lr
        }

        container orders_service {
            include *
            autolayout lr
        }

        dynamic services_service "poisk_uslugi" {
            user -> web_ui "Вводит параметры поиска"
            web_ui -> web_backend "Передает запрос на поиск"
            web_backend -> services_api "Запрашивает поиск"
            services_api -> services_database "Запрашивает данные"
            services_database -> services_api "Возвращает результаты поиска"
            services_api -> web_backend "Возвращает результаты поиска"
            web_backend -> web_ui "Передает результаты поиска"
            web_ui -> user "Отображает список услуг"
        }
    }
}
