# Telegram Subpages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Разделить монолитную TelegramPage.tsx на 3 подстраницы: список аккаунтов, чаты+сообщения, настройки.

**Architecture:** Три отдельных страницы, каждая со своим роутом. `selectedAccountId` и `selectedChatId` переезжают из `useState` в URL (`useParams`). Все API-запросы и queryKey без изменений.

**Tech Stack:** React 18, TypeScript, Ant Design 5, React Router v6, @tanstack/react-query

---

### Task 1: Создать TelegramAccountsPage.tsx

**Files:**
- Create: `frontend/src/pages/telegram/TelegramAccountsPage.tsx`
- Delete later: `frontend/src/pages/telegram/TelegramPage.tsx`

- [ ] **Step 1: Создать TelegramAccountsPage.tsx**

Содержит блок подключения аккаунта (SMS + QR) и таблицу аккаунтов. Клик по строке таблицы → `navigate(/telegram/${id}/chats)`.

```tsx
import { useState } from 'react';
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  Popconfirm,
  Radio,
  Row,
  Space,
  Steps,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { QRCodeSVG } from 'qrcode.react';
import { useNavigate } from 'react-router-dom';
import { PageTitle } from '../../components/common/PageTitle';
import { AccountRead, TelegramClientsService } from '../../api/generated';
import { formatDate } from '../../utils/formatters';
import { extractErrorMessage } from '../../utils/api';

export function TelegramAccountsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [phoneForm] = Form.useForm<{ phone: string }>();
  const [codeForm] = Form.useForm<{ code: string }>();
  const [passwordForm] = Form.useForm<{ password: string }>();
  const [wizardStep, setWizardStep] = useState(0);
  const [pendingAccountId, setPendingAccountId] = useState<string | null>(null);
  const [authMethod, setAuthMethod] = useState<'sms' | 'qr'>('sms');
  const [qrAccountId, setQrAccountId] = useState<string | null>(null);
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [qrStatus, setQrStatus] = useState<string>('pending');
  const [qrMessage, setQrMessage] = useState<string | null>(null);
  const [qrLoading, setQrLoading] = useState(false);

  const accountsQuery = useQuery({
    queryKey: ['telegram', 'accounts'],
    queryFn: () => TelegramClientsService.getAccountsApiV1PublicTelegramGet(undefined, 1, 100),
  });

  const phoneMutation = useMutation({
    mutationFn: (values: { phone: string }) => TelegramClientsService.authPhoneApiV1PublicTelegramAuthPhonePost(values),
    onSuccess: (response) => {
      setPendingAccountId(response.account_id);
      setWizardStep(1);
      void message.success('Код отправлен');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });
  const codeMutation = useMutation({
    mutationFn: (values: { code: string }) =>
      TelegramClientsService.authCodeApiV1PublicTelegramAuthCodePost({
        account_id: pendingAccountId!,
        code: values.code,
      }),
    onSuccess: (response) => {
      if (response.status === '2fa_required') {
        setWizardStep(2);
        void message.info('Требуется 2FA пароль');
      } else {
        setWizardStep(0);
        setPendingAccountId(null);
        phoneForm.resetFields();
        codeForm.resetFields();
        void queryClient.invalidateQueries({ queryKey: ['telegram'] });
        void message.success('Telegram-аккаунт подключён');
      }
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });
  const passwordMutation = useMutation({
    mutationFn: (values: { password: string }) =>
      TelegramClientsService.authPasswordApiV1PublicTelegramAuthPasswordPost({
        account_id: pendingAccountId!,
        password: values.password,
      }),
    onSuccess: () => {
      setWizardStep(0);
      setPendingAccountId(null);
      phoneForm.resetFields();
      codeForm.resetFields();
      passwordForm.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['telegram'] });
      void message.success('Telegram-аккаунт подключён');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });
  const deleteMutation = useMutation({
    mutationFn: (accountId: string) =>
      TelegramClientsService.deleteAccountApiV1PublicTelegramAccountIdDelete(accountId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['telegram'] });
      void message.success('Аккаунт удалён');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });
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
  const qrCancelMutation = useMutation({
    mutationFn: () =>
      TelegramClientsService.authQrCancelApiV1PublicTelegramAuthQrAccountIdDelete(qrAccountId!),
    onSuccess: () => {
      setQrAccountId(null);
      setQrUrl(null);
      setQrStatus('pending');
      setQrMessage(null);
      void message.info('QR-авторизация отменена');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  // Polling QR status
  const [qrPollInterval, setQrPollInterval] = useState<ReturnType<typeof setInterval> | null>(null);
  const startQrPolling = () => {
    const interval = setInterval(async () => {
      if (!qrAccountId) return;
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
    setQrPollInterval(interval);
  };

  // Start polling when qrAccountId changes
  const prevQrAccountIdRef = useRef<string | null>(null);
  useEffect(() => {
    if (qrAccountId && qrAccountId !== prevQrAccountIdRef.current) {
      prevQrAccountIdRef.current = qrAccountId;
      if (qrPollInterval) clearInterval(qrPollInterval);
      startQrPolling();
    }
    return () => {
      if (qrPollInterval) clearInterval(qrPollInterval);
    };
  }, [qrAccountId]);

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle title="Telegram" subtitle="Пошаговое подключение аккаунта, чаты, сообщения и настройки чтения" />
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={9}>
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
        </Col>
        <Col xs={24} xl={15}>
          <Card title="Аккаунты">
            <Table
              rowKey="id"
              loading={accountsQuery.isLoading}
              dataSource={accountsQuery.data?.items ?? []}
              pagination={false}
              onRow={(record: AccountRead) => ({
                onClick: () => navigate(`/telegram/${record.id}/chats`),
                style: { cursor: 'pointer' },
              })}
              columns={[
                { title: 'Phone', dataIndex: 'phone' },
                {
                  title: 'Status',
                  dataIndex: 'is_connected',
                  render: (value: boolean) => (
                    <Tag color={value ? 'success' : 'default'}>{value ? 'connected' : 'pending'}</Tag>
                  ),
                },
                { title: 'Username', dataIndex: 'username', render: (value: string | null) => value ?? '-' },
                { title: 'Created', dataIndex: 'created_at', render: (value: string) => formatDate(value) },
                {
                  title: 'Action',
                  render: (_: unknown, record: AccountRead) => (
                    <Popconfirm title="Удалить аккаунт?" onConfirm={() => deleteMutation.mutate(record.id)}>
                      <Button size="small" danger>
                        Удалить
                      </Button>
                    </Popconfirm>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
```

Note: нужно добавить `useRef` в импорты React.

- [ ] **Step 2: Проверить сборку**

Run: `cd /home/work/23066359@sigma.sbrf.ru/IdeaProjects/ms_starter/frontend && npx tsc --noEmit`
Expected: OK (может быть ошибка на отсутствие импорта в router.tsx — игнорируем, исправим в Task 4)

---

### Task 2: Создать TelegramChatsPage.tsx

**Files:**
- Create: `frontend/src/pages/telegram/TelegramChatsPage.tsx`

- [ ] **Step 1: Создать TelegramChatsPage.tsx**

Содержит список чатов (слева) и сообщения (справа). `accountId` из `useParams`, `selectedChatId` из `useState`.

```tsx
import { useState } from 'react';
import { Button, Card, Col, Empty, List, Row, Space, Tag, Typography } from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { PageTitle } from '../../components/common/PageTitle';
import { ChatRead, TelegramClientsService } from '../../api/generated';
import { formatDate } from '../../utils/formatters';

export function TelegramChatsPage() {
  const { accountId } = useParams<{ accountId: string }>();
  const navigate = useNavigate();
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null);

  const accountQuery = useQuery({
    queryKey: ['telegram', 'account', accountId],
    enabled: Boolean(accountId),
    queryFn: () => TelegramClientsService.getAccountApiV1PublicTelegramAccountIdGet(accountId!),
  });

  const chatsQuery = useQuery({
    queryKey: ['telegram', 'chats', accountId],
    enabled: Boolean(accountId),
    queryFn: () => TelegramClientsService.getChatsApiV1PublicTelegramAccountIdChatsGet(accountId!, 100),
  });

  const messagesQuery = useQuery({
    queryKey: ['telegram', 'messages', accountId, selectedChatId],
    enabled: Boolean(accountId && selectedChatId !== null),
    queryFn: () =>
      TelegramClientsService.getMessagesApiV1PublicTelegramAccountIdChatsChatIdMessagesGet(
        accountId!,
        selectedChatId!,
        50,
      ),
  });

  const phone = accountQuery.data?.phone ?? `Аккаунт ${accountId}`;

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle
        title={`Чаты — ${phone}`}
        subtitle="Просмотр чатов и сообщений Telegram-аккаунта"
        extra={
          <Button
            icon={<SettingOutlined />}
            onClick={() => navigate(`/telegram/${accountId}/settings`)}
          >
            Настройки
          </Button>
        }
      />
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={10}>
          <Card title="Чаты аккаунта">
            <List
              loading={chatsQuery.isLoading}
              dataSource={chatsQuery.data ?? []}
              locale={{ emptyText: <Empty description="Нет чатов" /> }}
              renderItem={(item: ChatRead) => (
                <List.Item
                  className={selectedChatId === item.id ? 'chat-row active' : 'chat-row'}
                  onClick={() => setSelectedChatId(item.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <List.Item.Meta title={item.name ?? item.username ?? item.id} description={item.chat_type} />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} xl={14}>
          <Card title="Сообщения">
            <List
              loading={messagesQuery.isLoading}
              dataSource={messagesQuery.data ?? []}
              locale={{ emptyText: <Empty description="Выберите чат" /> }}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    title={`#${item.id} / ${formatDate(item.date)}`}
                    description={
                      <Space direction="vertical" size={4}>
                        <Typography.Text>{item.text ?? '(без текста)'}</Typography.Text>
                        {item.media?.length ? <Tag color="blue">media: {item.media.length}</Tag> : null}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
```

- [ ] **Step 2: Проверить сборку**

Run: `cd /home/work/23066359@sigma.sbrf.ru/IdeaProjects/ms_starter/frontend && npx tsc --noEmit`
Expected: OK

---

### Task 3: Создать TelegramSettingsPage.tsx

**Files:**
- Create: `frontend/src/pages/telegram/TelegramSettingsPage.tsx`

- [ ] **Step 1: Создать TelegramSettingsPage.tsx**

Содержит форму настроек чтения. `accountId` из `useParams`.

```tsx
import { useEffect } from 'react';
import { Button, Card, Form, Input, Space, Switch, message } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { PageTitle } from '../../components/common/PageTitle';
import { ApiError, TelegramClientsService } from '../../api/generated';
import { extractErrorMessage } from '../../utils/api';

export function TelegramSettingsPage() {
  const { accountId } = useParams<{ accountId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [settingsForm] = Form.useForm<{
    read_groups: boolean;
    read_personal: boolean;
    read_channels: boolean;
    whitelist_chat_ids: string;
  }>();

  const accountQuery = useQuery({
    queryKey: ['telegram', 'account', accountId],
    enabled: Boolean(accountId),
    queryFn: () => TelegramClientsService.getAccountApiV1PublicTelegramAccountIdGet(accountId!),
  });

  const settingsQuery = useQuery({
    queryKey: ['telegram', 'settings', accountId],
    enabled: Boolean(accountId),
    queryFn: () => TelegramClientsService.getSettingsApiV1PublicTelegramAccountIdSettingsGet(accountId!),
  });

  useEffect(() => {
    if (settingsQuery.data) {
      settingsForm.setFieldsValue({
        read_groups: settingsQuery.data.read_groups,
        read_personal: settingsQuery.data.read_personal,
        read_channels: settingsQuery.data.read_channels,
        whitelist_chat_ids: settingsQuery.data.whitelist_chat_ids.join(', '),
      });
    } else if (settingsQuery.error instanceof ApiError && settingsQuery.error.status === 404) {
      settingsForm.setFieldsValue({
        read_groups: true,
        read_personal: true,
        read_channels: false,
        whitelist_chat_ids: '',
      });
    }
  }, [settingsForm, settingsQuery.data, settingsQuery.error]);

  const settingsMutation = useMutation({
    mutationFn: async (values: {
      read_groups: boolean;
      read_personal: boolean;
      read_channels: boolean;
      whitelist_chat_ids: string;
    }) => {
      const whitelistChatIds = values.whitelist_chat_ids
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);

      if (settingsQuery.data) {
        return TelegramClientsService.updateSettingsApiV1PublicTelegramAccountIdSettingsPut(accountId!, {
          read_groups: values.read_groups,
          read_personal: values.read_personal,
          read_channels: values.read_channels,
        });
      }

      return TelegramClientsService.createSettingsApiV1PublicTelegramAccountIdSettingsPost(accountId!, {
        read_groups: values.read_groups,
        read_personal: values.read_personal,
        read_channels: values.read_channels,
        whitelist_chat_ids: whitelistChatIds,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['telegram', 'settings', accountId] });
      void message.success('Настройки сохранены');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const phone = accountQuery.data?.phone ?? `Аккаунт ${accountId}`;

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle
        title={`Настройки — ${phone}`}
        subtitle="Настройки чтения Telegram-аккаунта"
        extra={
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/telegram/${accountId}/chats`)}>
            Назад к чатам
          </Button>
        }
      />
      <Card title="Настройки чтения">
        <Form layout="vertical" form={settingsForm} onFinish={(values) => settingsMutation.mutate(values)} style={{ maxWidth: 480 }}>
          <Form.Item name="read_groups" label="Read groups" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="read_personal" label="Read personal" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="read_channels" label="Read channels" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="whitelist_chat_ids" label="Whitelist chat ids">
            <Input.TextArea rows={4} placeholder="1, 2, -100123..." />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={settingsMutation.isPending}>
            Сохранить настройки
          </Button>
        </Form>
      </Card>
    </Space>
  );
}
```

- [ ] **Step 2: Проверить сборку**

Run: `cd /home/work/23066359@sigma.sbrf.ru/IdeaProjects/ms_starter/frontend && npx tsc --noEmit`
Expected: OK

---

### Task 4: Обновить router.tsx

**Files:**
- Modify: `frontend/src/router.tsx`

- [ ] **Step 1: Заменить импорт и роуты**

Заменить:
```tsx
import { TelegramPage } from './pages/telegram/TelegramPage';
```
на:
```tsx
import { TelegramAccountsPage } from './pages/telegram/TelegramAccountsPage';
import { TelegramChatsPage } from './pages/telegram/TelegramChatsPage';
import { TelegramSettingsPage } from './pages/telegram/TelegramSettingsPage';
```

Заменить:
```tsx
<Route path="telegram" element={<TelegramPage />} />
```
на:
```tsx
<Route path="telegram" element={<TelegramAccountsPage />} />
<Route path="telegram/:accountId/chats" element={<TelegramChatsPage />} />
<Route path="telegram/:accountId/settings" element={<TelegramSettingsPage />} />
```

- [ ] **Step 2: Проверить сборку**

Run: `cd /home/work/23066359@sigma.sbrf.ru/IdeaProjects/ms_starter/frontend && npx tsc --noEmit`
Expected: OK

---

### Task 5: Обновить ProtectedLayout.tsx (breadcrumbs)

**Files:**
- Modify: `frontend/src/components/layout/ProtectedLayout.tsx`

- [ ] **Step 1: Добавить breadcrumbs для новых путей**

В объект `breadcrumbMap` добавить:
```tsx
    chats: 'Chats',
    settings: 'Settings',
```

Также нужно обновить `selectedKey` в меню, чтобы при нахождении на `/telegram/:accountId/chats` или `/telegram/:accountId/settings` подсвечивался пункт "Telegram". Сейчас `location.pathname.startsWith(key)` с `key = '/telegram'` уже корректно работает для всех подпутей, так что меню менять не нужно.

- [ ] **Step 2: Проверить сборку**

Run: `cd /home/work/23066359@sigma.sbrf.ru/IdeaProjects/ms_starter/frontend && npx tsc --noEmit`
Expected: OK

---

### Task 6: Удалить старый TelegramPage.tsx

**Files:**
- Delete: `frontend/src/pages/telegram/TelegramPage.tsx`

- [ ] **Step 1: Удалить файл**

```bash
rm /home/work/23066359@sigma.sbrf.ru/IdeaProjects/ms_starter/frontend/src/pages/telegram/TelegramPage.tsx
```

- [ ] **Step 2: Проверить сборку**

Run: `cd /home/work/23066359@sigma.sbrf.ru/IdeaProjects/ms_starter/frontend && npx tsc --noEmit`
Expected: OK, no errors

---

### Task 7: Финальная проверка

**Files:**
- Проверить: весь проект

- [ ] **Step 1: Полная сборка**

Run: `cd /home/work/23066359@sigma.sbrf.ru/IdeaProjects/ms_starter/frontend && npm run build`
Expected: Build successful, no errors

- [ ] **Step 2: Линтер**

Run: `cd /home/work/23066359@sigma.sbrf.ru/IdeaProjects/ms_starter/frontend && npx eslint src/`
Expected: No errors (or pre-existing warnings only)

- [ ] **Step 3: Закоммитить**

```bash
git add frontend/src/pages/telegram/TelegramAccountsPage.tsx \
        frontend/src/pages/telegram/TelegramChatsPage.tsx \
        frontend/src/pages/telegram/TelegramSettingsPage.tsx \
        frontend/src/router.tsx \
        frontend/src/components/layout/ProtectedLayout.tsx
git rm frontend/src/pages/telegram/TelegramPage.tsx
git commit -m "feat: split TelegramPage into accounts, chats and settings subpages"
```