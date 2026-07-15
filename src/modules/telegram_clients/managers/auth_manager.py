"""
Менеджер авторизации Telegram-клиентов.

Отвечает за:
- Отправка SMS-кода
- Вход по SMS-коду
- Вход по паролю (2FA)
- QR-авторизация
"""

import asyncio
import contextlib
import logging
import uuid
from typing import Any

from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.constants import QrAuthStatus

logger = logging.getLogger(__name__)


class TelegramAuthManager:
    """
    Менеджер авторизации Telegram-клиентов.

    Содержит логику отправки кодов, входа по коду/паролю и QR-авторизации.
    Для создания клиентов и управления сессиями использует TelegramSessionManager.
    """

    def __init__(self, client_manager: Any) -> None:
        """
        Args:
            client_manager: Ссылка на TelegramClientManager (фасад),
                            через который получает доступ к _clients, get_session_path,
                            create_client, register_message_handler.
        """
        self._client_manager = client_manager
        self._phone_code_hashes: dict[uuid.UUID, str] = {}
        self._phones: dict[uuid.UUID, str] = {}
        self._qr_sessions: dict[uuid.UUID, dict[str, str]] = {}
        self._qr_tasks: dict[uuid.UUID, asyncio.Task[None]] = {}

    async def send_code(self, phone: str, account_id: uuid.UUID) -> str:
        """
        Отправить SMS-код на номер телефона.

        Создаёт временный клиент, отправляет код и возвращает
        phone_code_hash для последующей верификации.
        """
        session_path = self._client_manager.get_session_path(account_id)
        logger.info(
            "[tg client] send_code start: account_id=%s, phone=%s, session_path=%s",
            account_id,
            phone,
            session_path,
        )
        client = self._client_manager.create_client(session_path)
        await client.connect()
        logger.info(
            "[tg client] connected to Telegram: account_id=%s, authorized=%s",
            account_id,
            await client.is_user_authorized(),
        )

        result = await client.send_code_request(phone)
        self._phone_code_hashes[account_id] = result.phone_code_hash

        # Логируем тип доставки кода (SMS / Telegram app / etc.)
        code_type = getattr(result, "type", None)
        timeout = getattr(result, "timeout", None)
        next_type = getattr(result, "next_type", None)
        logger.info(
            "[tg client] send_code done: account_id=%s, phone_code_hash=%s, "
            "code_type=%s, timeout=%s, next_type=%s",
            account_id,
            result.phone_code_hash,
            code_type,
            timeout,
            next_type,
        )

        # Сохраняем номер для последующего sign_in, т.к. Telethon его не хранит
        self._phones[account_id] = phone

        # Клиент будет переиспользован при sign_in
        self._client_manager.set_client(account_id, client)
        return result.phone_code_hash

    async def sign_in_with_code(self, account_id: uuid.UUID, code: str) -> str:
        """
        Войти по SMS-коду.

        Возвращает "connected", "2fa_required" или "invalid_code".
        """
        client = self._client_manager.get_client(account_id)
        if not client:
            logger.error("[tg client] sign_in: клиент не найден для account_id=%s", account_id)
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не найден")

        phone_code_hash = self._phone_code_hashes.get(account_id, "")
        phone = self._phones.get(account_id, "")
        logger.info(
            "[tg client] sign_in start: account_id=%s, phone=%s, code=%s, phone_code_hash=%s",
            account_id,
            phone,
            code,
            phone_code_hash,
        )

        try:
            await client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=phone_code_hash,
            )
            # Авторизация успешна — регистрируем обработчик входящих
            self._client_manager.register_message_handler(account_id, client)
            logger.info("[tg client] sign_in connected: account_id=%s", account_id)
            return "connected"
        except SessionPasswordNeededError:
            logger.info("[tg client] sign_in 2fa required: account_id=%s", account_id)
            return "2fa_required"
        except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
            logger.warning(
                "[tg client] sign_in invalid/expired code: account_id=%s, %s",
                account_id,
                e,
            )
            return "invalid_code"
        except Exception as e:
            logger.exception("[tg client] sign_in error: account_id=%s, %s", account_id, e)
            raise

    async def sign_in_with_password(self, account_id: uuid.UUID, password: str) -> str:
        """Войти по паролю облачного шифрования (2FA)."""
        client = self._client_manager.get_client(account_id)
        if not client:
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не найден")

        await client.sign_in(password=password)
        self._client_manager.register_message_handler(account_id, client)
        return "connected"

    # ── QR-авторизация ─────────────────────────────────────────────

    async def _qr_wait_worker(self, account_id: uuid.UUID, client: TelegramClient, qr: Any) -> None:
        """Фоновый worker: ждёт сканирования QR-кода."""
        try:
            await qr.wait()
            self._qr_sessions[account_id] = {"status": QrAuthStatus.CONNECTED}
            self._client_manager.register_message_handler(account_id, client)
            logger.info("[tg client] QR login connected: account_id=%s", account_id)
        except TimeoutError:
            self._qr_sessions[account_id] = {
                "status": QrAuthStatus.EXPIRED,
                "message": "QR-код истёк",
            }
            logger.warning("[tg client] QR login expired: account_id=%s", account_id)
        except Exception as e:
            self._qr_sessions[account_id] = {
                "status": QrAuthStatus.ERROR,
                "message": str(e),
            }
            logger.exception("[tg client] QR login error: account_id=%s, %s", account_id, e)

    async def start_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
        """
        Запустить QR-авторизацию.

        Создаёт временный клиент, запускает qr_login() и фоновый worker.
        Возвращает данные для QR-кода.
        """
        session_path = self._client_manager.get_session_path(account_id)
        client = self._client_manager.create_client(session_path)
        await client.connect()

        qr = await client.qr_login()
        expires_at: float | None = getattr(qr, "timeout", None)

        self._client_manager.set_client(account_id, client)
        self._qr_sessions[account_id] = {"status": QrAuthStatus.PENDING}

        task = asyncio.create_task(self._qr_wait_worker(account_id, client, qr))
        self._qr_tasks[account_id] = task

        logger.info(
            "[tg client] QR login started: account_id=%s, expires_at=%s",
            account_id,
            expires_at,
        )

        return {
            "qr_url": qr.url,
            "expires_at": expires_at,
        }

    def get_qr_status(self, account_id: uuid.UUID) -> dict[str, str]:
        """
        Получить статус QR-сессии.

        Возвращает {"status": ..., "message": ...}.
        """
        session = self._qr_sessions.get(account_id)
        if not session:
            return {"status": QrAuthStatus.ERROR, "message": "QR-сессия не найдена"}
        return dict(session)

    async def cancel_qr_login(self, account_id: uuid.UUID) -> None:
        """Отменить QR-авторизацию: остановить worker, отключить клиент, очистить данные."""
        task = self._qr_tasks.pop(account_id, None)
        if task and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        client = self._client_manager.remove_client(account_id)
        if client:
            await client.disconnect()

        self._qr_sessions.pop(account_id, None)
        logger.info("[tg client] QR login cancelled: account_id=%s", account_id)

    async def complete_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
        """
        Завершить QR-авторизацию: получить данные пользователя из Telegram.

        Вызывается после того, как статус стал connected.
        """
        client = self._client_manager.get_client(account_id)
        if not client:
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не найден")

        me = await client.get_me()
        self._qr_sessions.pop(account_id, None)
        self._qr_tasks.pop(account_id, None)

        return {
            "first_name": me.first_name,
            "last_name": me.last_name,
            "username": me.username,
            "telegram_id": me.id,
        }
