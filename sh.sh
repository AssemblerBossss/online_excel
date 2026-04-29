#!/bin/bash

# Скрипт для создания структуры тестов в проекте online_excel
# Запускать из корневой директории проекта (online_excel/)

set -e  # остановка при любой ошибке

echo "🚀 Создание структуры тестов..."

# Создаем корневую директорию tests
mkdir -p tests

# Создаем основные директории
mkdir -p tests/unit/auth_service
mkdir -p tests/unit/table_service
mkdir -p tests/unit/api_gateway

mkdir -p tests/integration/auth_service
mkdir -p tests/integration/table_service
mkdir -p tests/integration/api_gateway

mkdir -p tests/e2e
mkdir -p tests/fixtures/excel_samples

# Создаем вложенные структуры для unit/auth_service
mkdir -p tests/unit/auth_service/test_services
mkdir -p tests/unit/auth_service/test_utils
mkdir -p tests/unit/auth_service/test_repository

# Создаем вложенные структуры для unit/table_service
mkdir -p tests/unit/table_service/test_services
mkdir -p tests/unit/table_service/test_models
mkdir -p tests/unit/table_service/test_repository

# Создаем вложенные структуры для unit/api_gateway
mkdir -p tests/unit/api_gateway/test_middleware
mkdir -p tests/unit/api_gateway/test_utils
mkdir -p tests/unit/api_gateway/test_routers

# Создаем вложенные структуры для integration/auth_service
mkdir -p tests/integration/auth_service/test_routers
mkdir -p tests/integration/auth_service/test_events
mkdir -p tests/integration/auth_service/test_repository

# Создаем вложенные структуры для integration/table_service
mkdir -p tests/integration/table_service/test_api
mkdir -p tests/integration/table_service/test_elastic
mkdir -p tests/integration/table_service/test_rabbitmq

# Создаем вложенные структуры для integration/api_gateway
mkdir -p tests/integration/api_gateway/test_routers
mkdir -p tests/integration/api_gateway/test_middleware

# Создаем __init__.py файлы для всех директорий
find tests -type d -exec touch {}/__init__.py \;

# Создаем основные файлы
touch tests/conftest.py
touch tests/pytest.ini
touch tests/.env.test

# Создаем примеры тестовых файлов (пустые)
touch tests/unit/auth_service/test_services/test_auth.py
touch tests/unit/auth_service/test_services/test_user.py
touch tests/unit/auth_service/test_utils/test_jwt_utils.py
touch tests/unit/auth_service/test_utils/test_security.py
touch tests/unit/auth_service/test_repository/test_user.py

touch tests/unit/table_service/test_services/test_table.py
touch tests/unit/table_service/test_services/test_data.py
touch tests/unit/table_service/test_services/test_excel_processor.py
touch tests/unit/table_service/test_models/test_table.py
touch tests/unit/table_service/test_models/test_data.py

touch tests/unit/api_gateway/test_middleware/test_auth.py
touch tests/unit/api_gateway/test_middleware/test_rate_limit.py
touch tests/unit/api_gateway/test_utils/test_jwt_handler.py
touch tests/unit/api_gateway/test_utils/test_proxy.py

touch tests/integration/auth_service/test_routers/test_auth_flow.py
touch tests/integration/auth_service/test_routers/test_user_flow.py
touch tests/integration/auth_service/test_events/test_rabbitmq_publisher.py

touch tests/integration/table_service/test_api/test_tables_endpoints.py
touch tests/integration/table_service/test_api/test_data_endpoints.py
touch tests/integration/table_service/test_elastic/test_search.py

touch tests/integration/api_gateway/test_routers/test_proxy.py

touch tests/e2e/test_full_user_journey.py
touch tests/e2e/test_table_crud_flow.py
touch tests/e2e/test_auth_table_integration.py

# Создаем примеры fixture файлов
cat > tests/fixtures/users.json << 'EOF'
[
  {
    "id": "test-user-1",
    "email": "test1@example.com",
    "firstname": "Test",
    "lastname": "User1"
  },
  {
    "id": "test-user-2",
    "email": "test2@example.com",
    "firstname": "Test",
    "lastname": "User2"
  }
]
EOF

cat > tests/fixtures/tables.json << 'EOF'
[
  {
    "id": "test-table-1",
    "name": "Test Table 1",
    "owner_id": "test-user-1"
  },
  {
    "id": "test-table-2",
    "name": "Test Table 2",
    "owner_id": "test-user-2"
  }
]
EOF

echo "✅ Структура тестов успешно создана!"
echo ""
echo "📁 Созданные директории:"
find tests -type d | sort
echo ""
echo "📄 Созданные файлы:"
find tests -type f | sort
