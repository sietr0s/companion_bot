import { useState } from 'react';
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import {
  InstagramAccountRead,
  InstagramAccountsService,
  InstagramClientsService,
  InstagramSettingsRead,
} from '../../api/generated';
import { extractErrorMessage, isConflict } from '../../utils/api';
import { formatDate } from '../../utils/formatters';

export function InstagramAccountsPage() {
  const queryClient = useQueryClient();
  const [createForm] = Form.useForm<{ username: string }>();
  const [loginForm] = Form.useForm<{ username: string; password: string; code?: string }>();
  const [whitelistForm] = Form.useForm<{ user_pk: number }>();
  const [loginAccount, setLoginAccount] = useState<InstagramAccountRead | null>(null);
  const [loginStep, setLoginStep] = useState<'password' | 'two_factor' | 'challenge'>('password');
  const [whitelistAccountId, setWhitelistAccountId] = useState<string | null>(null);

  const accountsQuery = useQuery({
    queryKey: ['instagram', 'accounts'],
    queryFn: () => InstagramAccountsService.getListApiV1PublicInstagramAccountsGet(1, 100),
  });

  const settingsQuery = useQuery({
    queryKey: ['instagram', 'settings', whitelistAccountId],
    queryFn: () =>
      InstagramClientsService.getSettingsApiV1PublicInstagramAccountIdSettingsGet(whitelistAccountId!),
    enabled: Boolean(whitelistAccountId),
  });

  const createMutation = useMutation({
    mutationFn: (values: { username: string }) =>
      InstagramAccountsService.createApiV1PublicInstagramAccountsPost(values),
    onSuccess: () => {
      createForm.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['instagram'] });
      void message.success('Аккаунт создан');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => InstagramAccountsService.deleteApiV1PublicInstagramAccountsItemIdDelete(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['instagram'] });
      void message.success('Аккаунт удалён');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const loginMutation = useMutation({
    mutationFn: async (values: { username: string; password: string; code?: string }) => {
      const id = loginAccount!.id;
      if (loginStep === 'two_factor') {
        return InstagramClientsService.twoFactorApiV1PublicInstagramAccountsAccountIdTwoFactorPost(id, {
          code: values.code ?? '',
        });
      }
      if (loginStep === 'challenge') {
        return InstagramClientsService.challengeApiV1PublicInstagramAccountsAccountIdChallengePost(id, {
          code: values.code ?? '',
        });
      }
      return InstagramClientsService.loginApiV1PublicInstagramAccountsAccountIdLoginPost(id, {
        username: values.username,
        password: values.password,
      });
    },
    onSuccess: () => {
      setLoginAccount(null);
      setLoginStep('password');
      loginForm.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['instagram'] });
      void message.success('Instagram-аккаунт подключён');
    },
    onError: (error: unknown) => {
      const detail = extractErrorMessage(error);
      if (isConflict(error) && detail === 'two_factor_required') {
        setLoginStep('two_factor');
        void message.info('Введите код 2FA');
        return;
      }
      if (isConflict(error) && detail === 'challenge_required') {
        setLoginStep('challenge');
        void message.info('Введите код challenge');
        return;
      }
      void message.error(detail);
    },
  });

  const whitelistAdd = useMutation({
    mutationFn: (userPk: number) =>
      InstagramClientsService.addUserToWhitelistApiV1PublicInstagramAccountIdWhitelistPost(
        whitelistAccountId!,
        { user_pk: userPk },
      ),
    onSuccess: () => {
      whitelistForm.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['instagram', 'settings', whitelistAccountId] });
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const whitelistRemove = useMutation({
    mutationFn: (userPk: number) =>
      InstagramClientsService.removeUserFromWhitelistApiV1PublicInstagramAccountIdWhitelistUserPkDelete(
        whitelistAccountId!,
        userPk,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['instagram', 'settings', whitelistAccountId] });
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const columns = [
    { title: 'Username', dataIndex: 'username' },
    { title: 'PK', dataIndex: 'instagram_pk' },
    {
      title: 'Статус',
      dataIndex: 'is_connected',
      render: (value: boolean) => (
        <Tag color={value ? 'green' : 'default'}>{value ? 'connected' : 'offline'}</Tag>
      ),
    },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      render: (value: string | null | undefined) => (value ? formatDate(value) : '—'),
    },
    {
      title: 'Действия',
      render: (_: unknown, record: InstagramAccountRead) => (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setLoginAccount(record);
              setLoginStep('password');
              loginForm.setFieldsValue({ username: record.username, password: undefined, code: undefined });
            }}
          >
            Войти
          </Button>
          <Button size="small" onClick={() => setWhitelistAccountId(record.id)}>
            Whitelist
          </Button>
          <Popconfirm title="Удалить аккаунт?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button size="small" danger>
              Удалить
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const settings: InstagramSettingsRead | undefined = settingsQuery.data;

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle title="Instagram" subtitle="Аккаунты Direct, логин и whitelist" />
      <Card title="Новый аккаунт">
        <Form layout="inline" form={createForm} onFinish={(v) => createMutation.mutate(v)}>
          <Form.Item name="username" rules={[{ required: true, message: 'username' }]}>
            <Input placeholder="username" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={createMutation.isPending}>
              Создать
            </Button>
          </Form.Item>
        </Form>
      </Card>
      {loginAccount ? (
        <Card title={`Логин: ${loginAccount.username}`}>
          <Form layout="vertical" form={loginForm} onFinish={(v) => loginMutation.mutate(v)}>
            {loginStep === 'password' ? (
              <>
                <Form.Item name="username" label="Username" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
                <Form.Item name="password" label="Пароль" rules={[{ required: true }]}>
                  <Input.Password />
                </Form.Item>
              </>
            ) : (
              <Form.Item name="code" label={loginStep === 'two_factor' ? 'Код 2FA' : 'Код challenge'} rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            )}
            <Space>
              <Button type="primary" htmlType="submit" loading={loginMutation.isPending}>
                Отправить
              </Button>
              <Button
                onClick={() => {
                  setLoginAccount(null);
                  setLoginStep('password');
                  loginForm.resetFields();
                }}
              >
                Отмена
              </Button>
            </Space>
          </Form>
        </Card>
      ) : null}
      {whitelistAccountId ? (
        <Card
          title="Whitelist"
          extra={
            <Button type="link" onClick={() => setWhitelistAccountId(null)}>
              Закрыть
            </Button>
          }
        >
          <Form layout="inline" form={whitelistForm} onFinish={(v) => whitelistAdd.mutate(Number(v.user_pk))}>
            <Form.Item name="user_pk" rules={[{ required: true }]}>
              <InputNumber placeholder="user pk" style={{ width: 180 }} />
            </Form.Item>
            <Form.Item>
              <Button htmlType="submit" loading={whitelistAdd.isPending}>
                Добавить
              </Button>
            </Form.Item>
          </Form>
          <Space wrap style={{ marginTop: 12 }}>
            {(settings?.whitelist_user_pks ?? []).map((pk) => (
              <Tag
                key={String(pk)}
                closable
                onClose={() => whitelistRemove.mutate(Number(pk))}
              >
                {String(pk)}
              </Tag>
            ))}
            {settingsQuery.isLoading ? <Typography.Text type="secondary">загрузка…</Typography.Text> : null}
          </Space>
        </Card>
      ) : null}
      <Card title={`Аккаунты (${accountsQuery.data?.total ?? 0})`}>
        <Table
          rowKey="id"
          loading={accountsQuery.isLoading}
          columns={columns}
          dataSource={accountsQuery.data?.items ?? []}
          pagination={false}
        />
      </Card>
    </Space>
  );
}
