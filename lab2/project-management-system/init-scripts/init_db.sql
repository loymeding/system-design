-- Включаем вывод уведомлений для отслеживания процесса
\set VERBOSITY verbose

-- Создаем функцию для логирования
CREATE OR REPLACE FUNCTION log_message(message text)
RETURNS void AS $$
BEGIN
    RAISE NOTICE '%', message;
END;
$$ LANGUAGE plpgsql;

-- Проверяем и создаем расширение uuid-ossp
SELECT log_message('Checking uuid-ossp extension...');
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Удаление существующих таблиц с учетом зависимостей
SELECT log_message('Dropping existing tables if they exist...');

DO $$ 
BEGIN
    -- Удаляем старые триггеры если они существуют
    DROP TRIGGER IF EXISTS log_user_deletion ON users;
    DROP TRIGGER IF EXISTS log_order_deletion ON orders;
    DROP TRIGGER IF EXISTS log_service_deletion ON services;
    DROP TRIGGER IF EXISTS update_users_updated_at ON users;
    DROP TRIGGER IF EXISTS update_orders_updated_at ON orders;
    DROP TRIGGER IF EXISTS update_services_updated_at ON services;
    
    -- Удаляем старые функции
    DROP FUNCTION IF EXISTS log_deletion() CASCADE;
    DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
    
    -- Удаляем таблицы в правильном порядке
    DROP TABLE IF EXISTS services CASCADE;
    DROP TABLE IF EXISTS orders CASCADE;
    DROP TABLE IF EXISTS users CASCADE;
    DROP TABLE IF EXISTS deletion_log CASCADE;

    
    RAISE NOTICE 'All existing objects dropped successfully';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error during cleanup: %', SQLERRM;
END $$;


-- Создаем таблицу для логирования удалений
SELECT log_message('Creating deletion_log table...');

CREATE TABLE deletion_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(50) NOT NULL,
    record_id UUID NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_by TEXT,
    additional_info JSONB,
    version INTEGER DEFAULT 1
);

-- Создаем основные таблицы
SELECT log_message('Creating users table...');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

SELECT log_message('Creating orders table...');

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    CONSTRAINT fk_orders_owner
        FOREIGN KEY (owner_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

SELECT log_message('Creating services table...');

CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    cost UUID NOT NULL DEFAULT 10000,
    order_id UUID NOT NULL,
    creator_id UUID NOT NULL,
    assignee_id UUID,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    CONSTRAINT fk_services_order
        FOREIGN KEY (order_id)
        REFERENCES orders(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_services_creator
        FOREIGN KEY (creator_id)
        REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_services_assignee
        FOREIGN KEY (assignee_id)
        REFERENCES users(id)
        ON DELETE SET NULL
);

-- Создаем индексы
SELECT log_message('Creating indexes...');

-- Индексы для users
CREATE INDEX idx_users_username ON users(username) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_deleted_at ON users(deleted_at) WHERE deleted_at IS NOT NULL;

-- Индексы для orders
CREATE INDEX idx_orders_name ON orders(name) WHERE deleted_at IS NULL;
CREATE INDEX idx_orders_owner ON orders(owner_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_orders_deleted_at ON orders(deleted_at) WHERE deleted_at IS NOT NULL;

-- Индексы для services
CREATE INDEX idx_services_title ON services(title) WHERE deleted_at IS NULL;
CREATE INDEX idx_services_cost ON services(cost) WHERE deleted_at IS NULL;
CREATE INDEX idx_services_order ON services(order_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_services_creator ON services(creator_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_services_assignee ON services(assignee_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_services_deleted_at ON services(deleted_at) WHERE deleted_at IS NOT NULL;

-- Создаем функции и триггеры
SELECT log_message('Creating functions and triggers...');

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггеры для обновления updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_services_updated_at
    BEFORE UPDATE ON services
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Функция для логирования удалений
CREATE OR REPLACE FUNCTION log_deletion()
RETURNS TRIGGER AS $$
DECLARE
    record_info jsonb;
BEGIN
    -- Формируем информацию о записи в зависимости от таблицы
    CASE TG_TABLE_NAME
        WHEN 'users' THEN
            record_info := jsonb_build_object(
                'username', OLD.username,
                'email', OLD.email,
                'is_admin', OLD.is_admin
            );
        WHEN 'orders' THEN
            record_info := jsonb_build_object(
                'name', OLD.name,
                'owner_id', OLD.owner_id,
                'description', OLD.description
            );
        WHEN 'services' THEN
            record_info := jsonb_build_object(
                'title', OLD.title,
                'order_id', OLD.order_id,
                'cost', OLD.cost,
                'priority', OLD.priority
            );
        ELSE
            record_info := jsonb_build_object('info', 'unknown table type');
    END CASE;

    -- Записываем информацию в лог
    INSERT INTO deletion_log (
        table_name, 
        record_id, 
        deleted_by,
        additional_info,
        version
    ) VALUES (
        TG_TABLE_NAME,
        OLD.id,
        session_user,
        record_info,
        COALESCE((
            SELECT MAX(version) + 1
            FROM deletion_log
            WHERE table_name = TG_TABLE_NAME
            AND record_id = OLD.id
        ), 1)
    );

    RETURN OLD;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to log deletion: %', SQLERRM;
        RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Триггеры для логирования удалений
CREATE TRIGGER log_user_deletion
    BEFORE DELETE ON users
    FOR EACH ROW
    EXECUTE FUNCTION log_deletion();

CREATE TRIGGER log_order_deletion
    BEFORE DELETE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION log_deletion();

CREATE TRIGGER log_service_deletion
    BEFORE DELETE ON services
    FOR EACH ROW
    EXECUTE FUNCTION log_deletion();

-- Вставляем тестовые данные
SELECT log_message('Inserting test data...');

-- Создаем admin пользователя (пароль: secret)
INSERT INTO users (username, email, hashed_password, is_admin) 
VALUES (
    'admin',
    'admin@example.com',
    '$2b$12$LQgjwKCdWwF.7TkU1LVyguXiYwnmHwPRl4wzh5EXh5GxXslTyJKJy',
    true
);

-- Создаем тестового пользователя
INSERT INTO users (username, email, hashed_password) 
VALUES (
    'test_user',
    'test@example.com',
    '$2b$12$LQgjwKCdWwF.7TkU1LVyguXiYwnmHwPRl4wzh5EXh5GxXslTyJKJy'
);

-- Создаем тестовые проекты
INSERT INTO orders (name, description, owner_id)
VALUES 
    ('Test order 1', 'Description for test order 1',
     (SELECT id FROM users WHERE username = 'admin')),
    ('Test order 2', 'Description for test order 2',
     (SELECT id FROM users WHERE username = 'test_user'));

-- Создаем тестовые задачи
INSERT INTO services (title, description, order_id, creator_id, assignee_id)
VALUES 
    ('service 1', 'Description for service 1',
     (SELECT id FROM orders WHERE name = 'Test order 1'),
     (SELECT id FROM users WHERE username = 'admin'),
     (SELECT id FROM users WHERE username = 'test_user')),
    ('service 2', 'Description for service 2',
     (SELECT id FROM orders WHERE name = 'Test order 1'),
     (SELECT id FROM users WHERE username = 'admin'),
     NULL);

-- Тестирование каскадного удаления
SELECT log_message('Testing cascade delete...');

DO $$ 
DECLARE 
    v_order_id UUID;
    v_services_before INTEGER;
    v_services_after INTEGER;
BEGIN
    -- Начинаем транзакцию
    BEGIN
        -- Получаем ID тестового проекта
        SELECT id INTO STRICT v_order_id
        FROM orders
        WHERE name = 'Test order 1';

        -- Подсчет задач до удаления
        SELECT COUNT(*) INTO v_services_before
        FROM services
        WHERE order_id = v_order_id;
        
        RAISE NOTICE 'Found % services before deletion', v_services_before;

        -- Удаление проекта
        DELETE FROM orders WHERE id = v_order_id;

        -- Подсчет задач после удаления
        SELECT COUNT(*) INTO v_services_after
        FROM services
        WHERE order_id = v_order_id;
        
        IF v_services_after > 0 THEN
            RAISE EXCEPTION 'Cascade delete failed: % orphaned services remain', v_services_after;
        END IF;

        -- Проверяем логи удаления
        IF NOT EXISTS (
            SELECT 1 
            FROM deletion_log 
            WHERE table_name = 'orders'
            AND record_id = v_order_id
        ) THEN
            RAISE WARNING 'Deletion was not logged properly';
        END IF;

        RAISE NOTICE 'Cascade delete successful: % services were removed', v_services_before;
        
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE EXCEPTION 'Test order not found';
        WHEN TOO_MANY_ROWS THEN
            RAISE EXCEPTION 'Multiple test orders found';
        WHEN OTHERS THEN
            RAISE EXCEPTION 'Error during cascade delete test: %', SQLERRM;
    END;
END;
$$ LANGUAGE plpgsql;

-- Проверяем успешность каскадного удаления
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM services t
        LEFT JOIN orders p ON t.order_id = p.id
        WHERE p.id IS NULL
        AND t.deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'Verification failed: orphaned services found';
    END IF;
END;
$$ LANGUAGE plpgsql;

SELECT log_message('Database initialization completed successfully!');

-- Проверяем финальное состояние
SELECT log_message('Final state verification...');

DO $$ 
DECLARE
    users_count INTEGER;
    orders_count INTEGER;
    services_count INTEGER;
    deletion_logs_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO users_count FROM users WHERE deleted_at IS NULL;
    SELECT COUNT(*) INTO orders_count FROM orders WHERE deleted_at IS NULL;
    SELECT COUNT(*) INTO services_count FROM services WHERE deleted_at IS NULL;
    SELECT COUNT(*) INTO deletion_logs_count FROM deletion_log;

    RAISE NOTICE 'Active users: %', users_count;
    RAISE NOTICE 'Active orders: %', orders_count;
    RAISE NOTICE 'Active services: %', services_count;
    RAISE NOTICE 'Deletion log entries: %', deletion_logs_count;
END;
$$ LANGUAGE plpgsql;