import { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  List,
  Popconfirm,
  Row,
  Space,
  Steps,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import { AccountRead, ApiError, ChatRead, TelegramClientsService } from '../../api/generated';
import { formatDate } from '../../utils/formatters';
import { extractErrorMessage } from '../../utils/api';

export function TelegramPage() {
  const queryClient = useQueryClient();
  const [phoneForm] = Form.useForm<{ phone: string }>();
  const [codeForm] = Form.useForm<{ code: string }>();
  const [passwordForm] = Form.useForm<{ password: string }>();
  const [settingsForm] = Form.useForm<{
    read_groups: boolean;
    read_personal: boolean;
    read_channels: boolean;
    whitelist_chat_ids: string;
  }>();
  const [wizardStep, setWizardStep] = useState(0);
  const [pendingAccountId, setPendingAccountId] = useState<string | null>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null);

  const accountsQuery = useQuery({
    queryKey: ['telegram', 'accounts'],
    queryFn: () => TelegramClientsService.getAccountsApiV1PublicTelegramGet(undefined, 1, 100),
  });
  const chatsQuery = useQuery({
    queryKey: ['telegram', 'chats', selectedAccountId],
    enabled: Boolean(selectedAccountId),
    queryFn: () => TelegramClientsService.getChatsApiV1PublicTelegramAccountIdChatsGet(selectedAccountId!, 100),
  });
  const messagesQuery = useQuery({
    queryKey: ['telegram', 'messages', selectedAccountId, selectedChatId],
    enabled: Boolean(selectedAccountId && selectedChatId !== null),
    queryFn: () =>
      TelegramClientsService.getMessagesApiV1PublicTelegramAccountIdChatsChatIdMessagesGet(
        selectedAccountId!,
        selectedChatId!,
        50
      ),
  });
  const settingsQuery = useQuery({
    queryKey: ['telegram', 'settings', selectedAccountId],
    enabled: Boolean(selectedAccountId),
    queryFn: () => TelegramClientsService.getSettingsApiV1PublicTelegramAccountIdSettingsGet(selectedAccountId!),
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
      setSelectedAccountId(null);
      setSelectedChatId(null);
      void message.success('Аккаунт удалён');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });
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
        // TelegramSettingsUpdate has whitelist_chat_ids as null, so we cast it
        return TelegramClientsService.updateSettingsApiV1PublicTelegramAccountIdSettingsPut(selectedAccountId!, {
          read_groups: values.read_groups,
          read_personal: values.read_personal,
          read_channels: values.read_channels,
        });
      }

      return TelegramClientsService.createSettingsApiV1PublicTelegramAccountIdSettingsPost(selectedAccountId!, {
        read_groups: values.read_groups,
        read_personal: values.read_personal,
        read_channels: values.read_channels,
        whitelist_chat_ids: whitelistChatIds,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['telegram', 'settings', selectedAccountId] });
      void message.success('Настройки сохранены');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle title="Telegram" subtitle="Пошаговое подключение аккаунта, чаты, сообщения и настройки чтения" />
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={9}>
          <Card title="Подключение аккаунта">
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
                onClick: () => {
                  setSelectedAccountId(record.id);
                  setSelectedChatId(null);
                },
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
      {selectedAccountId ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={8}>
            <Card title="Чаты аккаунта">
              <List
                loading={chatsQuery.isLoading}
                dataSource={chatsQuery.data ?? []}
                locale={{ emptyText: <Empty description="Нет чатов" /> }}
                renderItem={(item: ChatRead) => (
                  <List.Item
                    className={selectedChatId === item.id ? 'chat-row active' : 'chat-row'}
                    onClick={() => setSelectedChatId(item.id)}
                  >
                    <List.Item.Meta title={item.name ?? item.username ?? item.id} description={item.chat_type} />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
          <Col xs={24} xl={8}>
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
          <Col xs={24} xl={8}>
            <Card title="Настройки аккаунта">
              <Form layout="vertical" form={settingsForm} onFinish={(values) => settingsMutation.mutate(values)}>
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
          </Col>
        </Row>
      ) : null}
    </Space>
  );
}
