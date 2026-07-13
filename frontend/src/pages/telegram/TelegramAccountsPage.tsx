import { useEffect, useRef, useState } from 'react';
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
  const qrPollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

    qrPollIntervalRef.current = interval;

    return () => clearInterval(interval);
  }, [qrAccountId, qrStatus, queryClient]);

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