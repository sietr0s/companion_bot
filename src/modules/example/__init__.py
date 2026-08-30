"""Example module - базовый модуль с CRUD операциями."""

from src.modules.example.model import ExampleModel
from src.modules.example.repository import ExampleRepository
from src.modules.example.service import ExampleService

__all__ = ["ExampleModel", "ExampleRepository", "ExampleService"]
