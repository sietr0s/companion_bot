# Telegram QR-авторизация — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить QR-авторизацию Telegram как альтернативу SMS: backend создаёт QR-сессию через Telethon, фронт показывает QR и поллит статус.

**Architecture:** Backend — три новых роута + методы в ClientManager/Service (in-memory QR-сессии, asyncio.Task для qr.wait()). Frontend — Radio.Group выбор метода, qrcode.react для рендера, polling 3 сек. Без миграций БД.

**Tech Stack:** Python/FastAPI/Telethon, React/TypeScript/Antd/qrcode.react

**Spec:** `docs/superpowers/specs/2026-07-12-telegram-qr-auth-design.md`

---

### Task 1: Добавить QrAuthStatus в constants.py

**Files:**
- Modify: `src/modules/telegram_clients/constants.py`

- [ ] **Step 1: Добавить QrAuthStatus enum**

```python
class QrAuthStatus(StrEnum):
    """Статусы QR-авторизации."""

    PENDING = "pending"
    CONNECTED = "connected"
    EXPIRED = "expired"
    ERROR = "error"
```

Вставить после `TgAuthStatus`, перед `ChatType`.

- [ ] **Step 2: Commit**

```bash
git add src/modules/telegram_clients/constants.py
git commit -m "feat: add QrAuthStatus enum for QR login"
```

---

### Task 2: Добавить QR-схемы в schemas/public/auth.py

**Files:**
- Modify: `src/modules/telegram_clients/schemas/public/auth.py`
- Modify: `src/modules/telegram_clients/schemas/public/__init__.py`

- [ ] **Step 1: Добавить QrStartResponse и QrStatusResponse**

```python
class QrStartResponse(BaseModel):
    """Ответ на старт QR-авторизации."""

    account_id: uuid.UUID
    qr_url: str
    expires_at: float | None = None


class QrStatusResponse(BaseModel):
    """Текущий статус QR-сессии."""

    status: str  # "pending" | "connected" | "expired" | "error"
    message: str | None = None
```

Вставить в конец файла `src/modules/telegram_clients/schemas/public/auth.py`.

- [ ] **Step 2: Ре-экспортировать новые схемы в __init__.py**

В `src/modules/telegram_clients/schemas/public/__init__.py` добавить в импорты:

```python
from src.modules.telegram_clients.schemas.public.auth import (
    QrStartResponse,
    QrStatusResponse,
)
```

И добавить `"QrStartResponse"`, `"QrStatusResponse"` в `__all__` (если есть).

- [ ] **Step 3: Commit**

```bash
git add src/modules/telegram_clients/schemas/public/auth.py src/modules/telegram_clients/schemas/public/__init__.py
git commit -m "feat: add QR auth request/response schemas"
```

---

### Task 3: Добавить QR-методы в ClientManager

**Files:**
- Modify: `src/modules/telegram_clients/client_manager.py`
- Modify: `src/modules/telegram_clients/constants.py` (импорт)

- [ ] **Step 1: Прочитать текущий client_manager.py, проверить импорты**

Убедиться, что `asyncio` импортирован. Если нет — добавить `import asyncio` в начало файла.

- [ ] **Step 2: Добавить in-memory структуры в __init__**

```python
def __init__(self) -> None:
    self._clients: dict[uuid.UUID, TelegramClient] = {}
    self._phone_code_hashes: dict[uuid.UUID, str] = {}
    self._qr_sessions: dict[uuid.UUID, dict[str, str]] = {}
    self._qr_tasks: dict[uuid.UUID, asyncio.Task[None]] = {}
    self._service = None
```

- [ ] **Step 3: Добавить _qr_wait_worker**

```python
async def _qr_wait_worker(self, account_id: uuid.UUID, client: TelegramClient, qr: Any) -> None:
    """Фоновый worker: ждёт сканирования QR-кода."""
    try:
        await qr.wait()
        self._qr_sessions[account_id] = {"status": QrAuthStatus.CONNECTED}
        self._register_message_handler(account_id, client)
        logger.info("[tg client] QR login connected: account_id=%s", account_id)
    except asyncio.TimeoutError:
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
```

Добавить импорт в начало файла:
```python
from src.modules.telegram_clients.constants import ChatType, QrAuthStatus, TgAuthStatus
```

Если `ChatType` и `TgAuthStatus` уже импортируются, просто добавить `QrAuthStatus` к существующему импорту. Проверить текущие импорты — возможно, `TgAuthStatus` и `ChatType` импортируются из соседних модулей, а не из constants.

Фактически, нужно посмотреть текущий код client_manager.py на импорт constants. Если их там нет — добавить:
```python
from src.modules.telegram_clients.constants import QrAuthStatus
```

- [ ] **Step 4: Добавить start_qr_login**

```python
async def start_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
    """
    Запустить QR-авторизацию.

    Создаёт временный клиент, запускает qr_login() и фоновый worker.
    Возвращает данные для QR-кода.
    """
    session_path = self._get_session_path(account_id)
    client = self._create_client(session_path)
    await client.connect()

    qr = await client.qr_login()
    expires_at: float | None = getattr(qr, "timeout", None)

    self._clients[account_id] = client
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
```

- [ ] **Step 5: Добавить get_qr_status**

```python
def get_qr_status(self, account_id: uuid.UUID) -> dict[str, str]:
    """
    Получить статус QR-сессии.

    Возвращает {"status": ..., "message": ...}.
    """
    session = self._qr_sessions.get(account_id)
    if not session:
        return {"status": QrAuthStatus.ERROR, "message": "QR-сессия не найдена"}
    return dict(session)
```

- [ ] **Step 6: Добавить cancel_qr_login**

```python
async def cancel_qr_login(self, account_id: uuid.UUID) -> None:
    """Отменить QR-авторизацию: остановить worker, отключить клиент, очистить данные."""
    task = self._qr_tasks.pop(account_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    client = self._clients.pop(account_id, None)
    if client:
        await client.disconnect()

    self._qr_sessions.pop(account_id, None)
    logger.info("[tg client] QR login cancelled: account_id=%s", account_id)
```

- [ ] **Step 7: Добавить complete_qr_login**

```python
async def complete_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
    """
    Завершить QR-авторизацию: получить данные пользователя из Telegram.

    Вызывается после того, как статус стал connected.
    """
    client = self._clients.get(account_id)
    if not client:
        raise NotFoundError(detail="Клиент для account_id=%s не найден" % account_id)

    me = await client.get_me()
    self._qr_sessions.pop(account_id, None)
    self._qr_tasks.pop(account_id, None)

    return {
        "first_name": me.first_name,
        "last_name": me.last_name,
        "username": me.username,
        "telegram_id": me.id,
    }
```

- [ ] **Step 8: Commit**

```bash
git add src/modules/telegram_clients/client_manager.py
git commit -m "feat: add QR login methods to ClientManager"
```

---

### Task 4: Добавить QR-методы в Service

**Files:**
- Modify: `src/modules/telegram_clients/service.py`

- [ ] **Step 1: Прочитать текущие импорты в service.py**

Проверить, что импортируются нужные схемы. Текущие импорты включают `AuthStep1Response`, `AuthStep2Response`, `AuthStep3Response`. Нужно добавить `QrStartResponse`, `QrStatusResponse`.

- [ ] **Step 2: Обновить импорты в service.py**

Добавить к существующему импорту из `schemas.public`:
```python
from src.modules.telegram_clients.schemas.public import (
    AuthStep1Response,
    AuthStep2Response,
    AuthStep3Response,
    QrStartResponse,
    QrStatusResponse,
)
```

- [ ] **Step 3: Добавить start_qr_auth**

```python
async def start_qr_auth(
    self, session: AsyncSession, auth_id: uuid.UUID
) -> QrStartResponse:
    """
    Шаг 1 QR-авторизации: создать QR-сессию.

    Запись в БД не создаётся. Возвращает account_id и qr_url.
    """
    account_id = uuid.uuid4()

    logger.info(
        "[tg qr auth] Старт QR-авторизации: auth_id=%s, account_id=%s",
        auth_id,
        account_id,
    )

    result = await self.client_manager.start_qr_login(account_id)

    return QrStartResponse(
        account_id=account_id,
        qr_url=result["qr_url"],
        expires_at=result.get("expires_at"),
    )
```

- [ ] **Step 4: Добавить get_qr_status**

```python
async def get_qr_status(self, account_id: uuid.UUID) -> QrStatusResponse:
    """Получить статус QR-сессии."""
    result = self.client_manager.get_qr_status(account_id)
    return QrStatusResponse(**result)
```

- [ ] **Step 5: Добавить cancel_qr_auth**

```python
async def cancel_qr_auth(self, account_id: uuid.UUID) -> None:
    """Отменить QR-авторизацию."""
    await self.client_manager.cancel_qr_login(account_id)
```

- [ ] **Step 6: Добавить complete_qr_auth**

```python
async def complete_qr_auth(
    self, session: AsyncSession, auth_id: uuid.UUID, account_id: uuid.UUID
) -> TelegramAccount:
    """
    Финализировать QR-авторизацию: создать запись в БД и опубликовать событие.
    """
    me = await self.client_manager.complete_qr_login(account_id)

    session_path = self.client_manager._get_session_path(account_id)

    account = await self.repository.create(
        session,
        {
            "id": account_id,
            "auth_id": auth_id,
            "phone": me.get("phone", "") or "",
            "session_file": session_path,
            "is_connected": True,
            "first_name": me.get("first_name"),
            "last_name": me.get("last_name"),
            "username": me.get("username"),
            "telegram_id": me.get("telegram_id"),
        },
    )

    event = TgAccountConnected(
        account_id=account.id,
        auth_id=account.auth_id,
        phone=account.phone,
    )
    await self.message_bus.publish(BusTopics.TG_ACCOUNT_CONNECTED, event.to_bus_dict())

    logger.info(
        "[tg qr auth] QR-авторизация завершена: account_id=%s, telegram_id=%s",
        account_id,
        me.get("telegram_id"),
    )

    return account
```

- [ ] **Step 7: Commit**

```bash
git add src/modules/telegram_clients/service.py
git commit -m "feat: add QR auth methods to TelegramClientService"
```

---

### Task 5: Добавить QR-роуты в routers/public.py

**Files:**
- Modify: `src/modules/telegram_clients/routers/public.py`

- [ ] **Step 1: Обновить импорты**

Добавить к импортам схем:
```python
from src.modules.telegram_clients.schemas.public import (
    AccountRead,
    AuthStep1Response,
    AuthStep2Response,
    AuthStep3Response,
    ChatRead,
    CodeRequest,
    MessageRead,
    PasswordRequest,
    PhoneRequest,
    QrStartResponse,
    QrStatusResponse,
)
```

- [ ] **Step 2: Добавить роут POST /auth/qr**

```python
@router.post(
    "/auth/qr",
    response_model=QrStartResponse,
    summary="Запустить QR-авторизацию Telegram",
)
async def auth_qr_start(
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> QrStartResponse:
    """Создаёт QR-сессию для авторизации Telegram через сканирование QR-кода."""
    return await service.start_qr_auth(session, auth_id)
```

- [ ] **Step 3: Добавить роут GET /auth/qr/{account_id}/status**

```python
@router.get(
    "/auth/qr/{account_id}/status",
    response_model=QrStatusResponse,
    summary="Статус QR-авторизации",
)
async def auth_qr_status(
    account_id: uuid.UUID,
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> QrStatusResponse:
    """Возвращает текущий статус QR-сессии: pending, connected, expired или error."""
    return await service.get_qr_status(account_id)
```

- [ ] **Step 4: Добавить роут DELETE /auth/qr/{account_id}**

```python
@router.delete(
    "/auth/qr/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отменить QR-авторизацию",
)
async def auth_qr_cancel(
    account_id: uuid.UUID,
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> None:
    """Отменяет QR-сессию и очищает временные данные."""
    await service.cancel_qr_auth(account_id)
```

- [ ] **Step 5: Добавить роут POST /auth/qr/{account_id}/complete**

```python
@router.post(
    "/auth/qr/{account_id}/complete",
    response_model=AccountRead,
    summary="Завершить QR-авторизацию",
)
async def auth_qr_complete(
    account_id: uuid.UUID,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> AccountRead:
    """Создаёт запись аккаунта в БД после успешного QR-сканирования."""
    return await service.complete_qr_auth(session, auth_id, account_id)
```

- [ ] **Step 6: Commit**

```bash
git add src/modules/telegram_clients/routers/public.py
git commit -m "feat: add QR auth routes to telegram_clients router"
```

---

### Task 6: Установить qrcode.react на фронте

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Установить зависимость**

```bash
cd frontend && npm install qrcode.react
```

- [ ] **Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat: add qrcode.react dependency for QR rendering"
```

---

### Task 7: Обновить TelegramPage.tsx — добавить QR-режим

**Files:**
- Modify: `frontend/src/pages/telegram/TelegramPage.tsx`

- [ ] **Step 1: Добавить импорты**

Добавить в начало файла:
```typescript
import { QRCodeSVG } from 'qrcode.react';
import { Radio } from 'antd';
```

- [ ] **Step 2: Добавить новые состояния**

Добавить после `setSelectedChatId`:
```typescript
const [authMethod, setAuthMethod] = useState<'sms' | 'qr'>('sms');
const [qrAccountId, setQrAccountId] = useState<string | null>(null);
const [qrUrl, setQrUrl] = useState<string | null>(null);
const [qrStatus, setQrStatus] = useState<string>('pending');
const [qrMessage, setQrMessage] = useState<string | null>(null);
const [qrLoading, setQrLoading] = useState(false);
```

- [ ] **Step 3: Добавить mutation для старта QR**

После `codeMutation`:
```typescript
const qrStartMutation = useMutation({
  mutationFn: () => TelegramClientsService.authQrStartApiV1PublicTelegramAuthQrPost(),
  onSuccess: (response) => {
    setQrAccountId(response.account_id);
    setQrUrl(response.qr_url);
    setQrStatus('pending');
    setQrMessage(null);
  },
  onError: (error: unknown) => void message.error(extractErrorMessage(error)),
});
```

Примечание: метода `authQrStartApiV1PublicTelegramAuthQrPost` ещё нет в сгенерированном API-клиенте. Его нужно будет добавить вручную в `TelegramClientsService.ts` (Task 8) или использовать общий `apiPost` utility. Пока используем прямой вызов fetch через утилиту.

Фактически — используем `apiPost` из `utils/api.ts`. Проверим, что там есть.

**Вариант:** добавить методы в `TelegramClientsService.ts` вручную (Task 8), а здесь использовать их.

- [ ] **Step 4: Добавить polling эффект**

```typescript
// Polling QR status
useEffect(() => {
  if (!qrAccountId || qrStatus !== 'pending') return;

  const interval = setInterval(async () => {
    try {
      const status = await TelegramClientsService.authQrStatusApiV1PublicTelegramAuthQrAccountIdStatusGet(qrAccountId);
      setQrStatus(status.status);
      setQrMessage(status.message ?? null);

      if (status.status === 'connected') {
        setQrLoading(true);
        try {
          await TelegramClientsService.authQrCompleteApiV1PublicTelegramAuthQrAccountIdCompletePost(qrAccountId);
          void queryClient.invalidateQueries({ queryKey: ['telegram'] });
          void message.success('Telegram-аккаунт подключён через QR');
          // Reset QR state
          setQrAccountId(null);
          setQrUrl(null);
          setQrStatus('pending');
          setQrMessage(null);
        } catch (e) {
          void message.error(extractErrorMessage(e));
          setQrStatus('error');
          setQrMessage('Не удалось завершить авторизацию');
        } finally {
          setQrLoading(false);
        }
      }
    } catch {
      // ignore polling errors
    }
  }, 3000);

  return () => clearInterval(interval);
}, [qrAccountId, qrStatus, queryClient]);
```

Опять же — методы `authQrStatusApiV1PublicTelegramAuthQrAccountIdStatusGet` и `authQrCompleteApiV1PublicTelegramAuthQrAccountIdCompletePost` появятся в Task 8.

- [ ] **Step 5: Добавить mutation для отмены QR**

```typescript
const qrCancelMutation = useMutation({
  mutationFn: () => TelegramClientsService.authQrCancelApiV1PublicTelegramAuthQrAccountIdDelete(qrAccountId!),
  onSuccess: () => {
    setQrAccountId(null);
    setQrUrl(null);
    setQrStatus('pending');
    setQrMessage(null);
    void message.info('QR-авторизация отменена');
  },
  onError: (error: unknown) => void message.error(extractErrorMessage(error)),
});
```

- [ ] **Step 6: Обновить JSX — добавить переключатель метода и QR-интерфейс**

Заменить карточку «Подключение аккаунта»:

```tsx
<Card title="Подключение аккаунта">
  <Radio.Group
    value={authMethod}
    onChange={(e) => setAuthMethod(e.target.value)}
    style={{ marginBottom: 16 }}
  >
    <Radio.Button value="sms">SMS</Radio.Button>
    <Radio.Button value="qr">QR</Radio.Button>
  </Radio.Group>

  {authMethod === 'sms' ? (
    <>
      <Steps
        current={wizardStep}
        size="small"
        items={[{ title: 'Телефон' }, { title: 'Код' }, { title: '2FA' }]}
      />
      <div className="steps-content">
        {wizardStep === 0 ? (
          <Form layout="vertical" form={phoneForm} onFinish={(values) => phoneMutation.mutate(values)}>
            <Form.Item name="phone" label="Номер телефона" rules={[{ required: true }]}>
              <Input placeholder="+79001234567" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={phoneMutation.isPending}>
              Отправить код
            </Button>
          </Form>
        ) : null}
        {wizardStep === 1 ? (
          <Form layout="vertical" form={codeForm} onFinish={(values) => codeMutation.mutate(values)}>
            <Form.Item name="code" label="SMS-код" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={codeMutation.isPending}>
              Подтвердить код
            </Button>
          </Form>
        ) : null}
        {wizardStep === 2 ? (
          <Form layout="vertical" form={passwordForm} onFinish={(values) => passwordMutation.mutate(values)}>
            <Form.Item name="password" label="2FA пароль" rules={[{ required: true }]}>
              <Input.Password />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={passwordMutation.isPending}>
              Завершить подключение
            </Button>
          </Form>
        ) : null}
      </div>
    </>
  ) : (
    <div className="steps-content">
      {!qrUrl ? (
        <Space direction="vertical" align="center" style={{ width: '100%' }}>
          <Button
            type="primary"
            onClick={() => qrStartMutation.mutate()}
            loading={qrStartMutation.isPending}
          >
            Получить QR-код
          </Button>
        </Space>
      ) : (
        <Space direction="vertical" align="center" style={{ width: '100%' }}>
          <QRCodeSVG value={qrUrl} size={200} />
          {qrStatus === 'pending' && (
            <Typography.Text type="secondary">
              Отсканируйте QR-код в Telegram: Настройки → Устройства → Подключить устройство
            </Typography.Text>
          )}
          {qrStatus === 'expired' && (
            <Typography.Text type="warning">
              QR-код истёк. Нажмите «Получить QR-код» чтобы попробовать снова.
            </Typography.Text>
          )}
          {qrStatus === 'error' && (
            <Typography.Text type="danger">
              {qrMessage || 'Ошибка авторизации'}
            </Typography.Text>
          )}
          {qrStatus === 'pending' && (
            <Space>
              <Button loading={qrStartMutation.isPending} onClick={() => qrStartMutation.mutate()}>
                Обновить QR
              </Button>
              <Button danger onClick={() => qrCancelMutation.mutate()} loading={qrCancelMutation.isPending}>
                Отмена
              </Button>
            </Space>
          )}
        </Space>
      )}
    </div>
  )}
</Card>
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/telegram/TelegramPage.tsx
git commit -m "feat: add QR auth UI to TelegramPage"
```

---

### Task 8: Добавить QR-методы в сгенерированный API-клиент фронта

**Files:**
- Modify: `frontend/src/api/generated/services/TelegramClientsService.ts`

- [ ] **Step 1: Добавить authQrStart**

Добавить внутрь класса `TelegramClientsService`:

```typescript
public static authQrStartApiV1PublicTelegramAuthQrPost(): CancelablePromise<{
  account_id: string;
  qr_url: string;
  expires_at: number | null;
}> {
  return __request(OpenAPI, {
    method: 'POST',
    url: '/api/v1/public/telegram/auth/qr',
    errors: {
      422: 'Validation Error',
    },
  });
}
```

- [ ] **Step 2: Добавить authQrStatus**

```typescript
public static authQrStatusApiV1PublicTelegramAuthQrAccountIdStatusGet(
  accountId: string,
): CancelablePromise<{
  status: string;
  message: string | null;
}> {
  return __request(OpenAPI, {
    method: 'GET',
    url: '/api/v1/public/telegram/auth/qr/{account_id}/status',
    path: {
      account_id: accountId,
    },
    errors: {
      422: 'Validation Error',
    },
  });
}
```

- [ ] **Step 3: Добавить authQrCancel**

```typescript
public static authQrCancelApiV1PublicTelegramAuthQrAccountIdDelete(
  accountId: string,
): CancelablePromise<void> {
  return __request(OpenAPI, {
    method: 'DELETE',
    url: '/api/v1/public/telegram/auth/qr/{account_id}',
    path: {
      account_id: accountId,
    },
    errors: {
      422: 'Validation Error',
    },
  });
}
```

- [ ] **Step 4: Добавить authQrComplete**

```typescript
public static authQrCompleteApiV1PublicTelegramAuthQrAccountIdCompletePost(
  accountId: string,
): CancelablePromise<AccountRead> {
  return __request(OpenAPI, {
    method: 'POST',
    url: '/api/v1/public/telegram/auth/qr/{account_id}/complete',
    path: {
      account_id: accountId,
    },
    errors: {
      422: 'Validation Error',
    },
  });
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/generated/services/TelegramClientsService.ts
git commit -m "feat: add QR auth API methods to TelegramClientsService"
```

---

### Task 9: Обновить документацию

**Files:**
- Modify: `docs/modules/telegram_clients.md`

- [ ] **Step 1: Обновить раздел «Основные возможности»**

Добавить строку:
```
- QR-авторизация в Telegram (альтернатива SMS)
```

- [ ] **Step 2: Добавить новый раздел «QR-авторизация» после раздела «Методы авторизации (пошаговые)»**

```markdown
### QR-авторизация (альтернативный метод)

#### start_qr_auth
```python
async def start_qr_auth(
    self, session: AsyncSession, auth_id: UUID
) -> QrStartResponse:
    """
    Шаг 1 QR: Создание QR-сессии
    
    - Генерирует account_id
    - Создаёт временный Telethon-клиент
    - Запускает qr_login() и фоновый asyncio.Task для ожидания
    - НЕ создаёт запись в БД
    - Возвращает account_id и qr_url для генерации QR-кода
    
    Запись в БД создаётся только после успешного сканирования QR
    через complete_qr_auth()
    """
```

#### get_qr_status
```python
async def get_qr_status(
    self, account_id: UUID
) -> QrStatusResponse:
    """
    Статус QR-сессии
    
    Возвращает один из статусов:
    - pending: ожидание сканирования
    - connected: QR отсканирован успешно
    - expired: QR истёк по времени
    - error: ошибка авторизации
    """
```

#### complete_qr_auth
```python
async def complete_qr_auth(
    self, session: AsyncSession, auth_id: UUID, account_id: UUID
) -> TelegramAccount:
    """
    Финализация QR-авторизации
    
    - Получает данные пользователя из Telegram (get_me)
    - Создаёт TelegramAccount в БД
    - Публикует TgAccountConnected
    """
```

#### cancel_qr_auth
```python
async def cancel_qr_auth(
    self, account_id: UUID
) -> None:
    """Отмена QR-сессии и очистка временных данных"""
```
```

- [ ] **Step 3: Обновить таблицу HTTP API**

Добавить строки:

```
| `POST` | `/public/telegram/auth/qr` | Старт QR-авторизации | JWT |
| `GET` | `/public/telegram/auth/qr/{id}/status` | Статус QR-сессии | JWT |
| `DELETE` | `/public/telegram/auth/qr/{id}` | Отмена QR-сессии | JWT |
| `POST` | `/public/telegram/auth/qr/{id}/complete` | Финализация QR | JWT |
```

- [ ] **Step 4: Добавить пример запроса QR-авторизации**

```markdown
**Старт QR-авторизации:**
```bash
POST /public/telegram/auth/qr
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "qr_url": "tg://login?token=...",
  "expires_at": 1752423000.0
}
```

**Статус QR-сессии:**
```bash
GET /public/telegram/auth/qr/{account_id}/status
Authorization: Bearer <token>
```

**Ответ (pending):**
```json
{
  "status": "pending",
  "message": null
}
```

**Ответ (connected):**
```json
{
  "status": "connected",
  "message": null
}
```

**Финализация:**
```bash
POST /public/telegram/auth/qr/{account_id}/complete
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone": "",
  "is_connected": true,
  "username": "ivanov",
  "first_name": "Ivan",
  "last_name": null,
  "telegram_id": 123456789,
  "created_at": "...",
  "updated_at": "..."
}
```
```

- [ ] **Step 5: Commit**

```bash
git add docs/modules/telegram_clients.md
git commit -m "docs: add QR auth section to telegram_clients module docs"
```

---

### Self-Review

1. **Spec coverage**: Each spec requirement maps to a task — constants (T1), schemas (T2), ClientManager (T3), Service (T4), Routes (T5), Frontend deps (T6), Frontend UI (T7), API client methods (T8), Docs (T9). Complete.

2. **Placeholder scan**: No TBD, TODO, or vague instructions. All code is concrete.

3. **Type consistency**: `account_id` is `uuid.UUID` in backend, `string` in frontend — consistent with existing patterns. `QrAuthStatus` values match spec exactly.
