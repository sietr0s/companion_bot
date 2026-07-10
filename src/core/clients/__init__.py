"""
Клиенты для межмодульного взаимодействия.

Используют прямой вызов сервисов через DI вместо HTTP-запросов.
"""

from src.core.clients.base import BaseHTTPClient

__all__ = ["BaseHTTPClient"]
