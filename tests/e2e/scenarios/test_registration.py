"""
E2E тест: Регистрация пользователя и подключение Telegram.

Сценарий:
1. POST /public/auth/register → создание пользователя
2. Проверка: пользователь создан, токен получен

Примечание: Полная интеграция с Telegram (SMS-код) требует
интерактивного ввода и тестируется отдельно.
"""
import pytest
import httpx
from uuid import uuid4


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_registration_flow(e2e_client: httpx.AsyncClient):
    """
    Полный цикл регистрации пользователя.
    
    Проверяет:
    - Регистрация с email
    - Возврат JWT токена
    - Корректная структура ответа
    """
    # Уникальный email для каждого запуска
    test_email = f"e2e_test_{uuid4()}@example.com"
    test_password = "TestPassword123!"
    
    register_data = {
        "identifier": test_email,
        "identifier_type": "email",
        "password": test_password
    }
    
    # Шаг 1: Регистрация
    response = await e2e_client.post("/public/auth/register", json=register_data)
    
    # Проверка статуса
    assert response.status_code == 201, f"Registration failed: {response.text}"
    
    # Проверка структуры ответа
    response_data = response.json()
    assert "access_token" in response_data, "Ответ должен содержать access_token"
    assert "token_type" in response_data, "Ответ должен содержать token_type"
    assert response_data["token_type"] == "bearer"
    
    # Проверка формата токена (JWT)
    token = response_data["access_token"]
    assert token.startswith("eyJ"), "Токен должен быть JWT"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_registration_with_phone(e2e_client: httpx.AsyncClient):
    """
    Регистрация с номером телефона.
    """
    test_phone = f"+7999{uuid4().int % 10000000:07d}"
    test_password = "TestPassword123!"
    
    register_data = {
        "identifier": test_phone,
        "identifier_type": "phone",
        "password": test_password
    }
    
    response = await e2e_client.post("/public/auth/register", json=register_data)
    
    assert response.status_code == 201, f"Phone registration failed: {response.text}"
    
    response_data = response.json()
    assert "access_token" in response_data


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_registration_duplicate_email(e2e_client: httpx.AsyncClient):
    """
    Регистрация с существующим email должна вернуть ошибку.
    """
    test_email = f"e2e_duplicate_{uuid4()}@example.com"
    test_password = "TestPassword123!"
    
    # Первая регистрация
    register_data = {
        "identifier": test_email,
        "identifier_type": "email",
        "password": test_password
    }
    
    response1 = await e2e_client.post("/public/auth/register", json=register_data)
    assert response1.status_code == 201
    
    # Вторая регистрация с тем же email
    response2 = await e2e_client.post("/public/auth/register", json=register_data)
    
    # Ожидаем конфликт (409) или другую ошибку
    assert response2.status_code in [409, 400], "Дубликат должен вернуть ошибку"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_login_after_registration(e2e_client: httpx.AsyncClient):
    """
    Вход после успешной регистрации.
    """
    test_email = f"e2e_login_{uuid4()}@example.com"
    test_password = "TestPassword123!"
    
    # Регистрация
    register_data = {
        "identifier": test_email,
        "identifier_type": "email",
        "password": test_password
    }
    
    await e2e_client.post("/public/auth/register", json=register_data)
    
    # Вход
    login_data = {
        "identifier": test_email,
        "password": test_password
    }
    
    response = await e2e_client.post("/public/auth/login", json=login_data)
    
    assert response.status_code == 200, f"Login failed: {response.text}"
    
    response_data = response.json()
    assert "access_token" in response_data
