import { useEffect } from 'react';
import {
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  Row,
  Space,
  Spin,
  Table,
  Typography,
  message,
} from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import {
  ApiError,
  InternalService,
  UsersService,
  src__modules__users__schemas__internal__user__UserRead as InternalUserRead,
} from '../../api/generated';
import { formatDate } from '../../utils/formatters';
import { extractErrorMessage } from '../../utils/api';

export function UsersPage() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<{ first_name?: string; last_name?: string; avatar_url?: string; bio?: string }>();

  const usersQuery = useQuery({
    queryKey: ['users', 'all'],
    queryFn: () => InternalService.getUsersInternalUsersGet(undefined, 1, 100),
  });
  const meQuery = useQuery({
    queryKey: ['users', 'me'],
    queryFn: () => UsersService.getMeApiV1PublicUsersMeGet(),
  });
  const telegramProfileQuery = useQuery({
    queryKey: ['users', 'me', 'telegram'],
    queryFn: () => UsersService.getMyTelegramApiV1PublicUsersMeTelegramGet(),
  });

  useEffect(() => {
    if (meQuery.data) {
      form.setFieldsValue({
        first_name: meQuery.data.first_name ?? '',
        last_name: meQuery.data.last_name ?? '',
        avatar_url: meQuery.data.avatar_url ?? '',
        bio: meQuery.data.bio ?? '',
      });
    }
  }, [form, meQuery.data]);

  const saveProfileMutation = useMutation({
    mutationFn: (values: { first_name?: string; last_name?: string; avatar_url?: string; bio?: string }) => {
      if (meQuery.data) {
        return UsersService.updateMeApiV1PublicUsersMePatch(values);
      }
      return UsersService.createProfileApiV1PublicUsersPost(values);
    },
    onSuccess: () => {
      void message.success('Профиль сохранён');
      void queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: unknown) => {
      void message.error(extractErrorMessage(error));
    },
  });

  const columns = [
    { title: 'ID', dataIndex: 'id', render: (value: string) => <Typography.Text code>{value}</Typography.Text> },
    {
      title: 'Auth ID',
      dataIndex: 'auth_id',
      render: (value: string) => <Typography.Text code>{value}</Typography.Text>,
    },
    {
      title: 'Имя',
      render: (_: unknown, record: InternalUserRead) =>
        [record.first_name, record.last_name].filter(Boolean).join(' ') || '-',
    },
    { title: 'Создан', dataIndex: 'created_at', render: (value: string) => formatDate(value) },
  ];

  const meProfileMissing = meQuery.error instanceof ApiError && meQuery.error.status === 404;
  const telegramProfileMissing =
    telegramProfileQuery.error instanceof ApiError && telegramProfileQuery.error.status === 404;

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle title="Users" subtitle="Internal user list + публичный профиль текущего пользователя" />
      <Card title="Список пользователей">
        <Table
          rowKey="id"
          loading={usersQuery.isLoading}
          columns={columns}
          dataSource={usersQuery.data?.items ?? []}
          pagination={false}
          scroll={{ x: 900 }}
        />
      </Card>
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <Card title="Мой профиль">
            {meQuery.isLoading ? (
              <Spin />
            ) : meProfileMissing || meQuery.data ? (
              <Form layout="vertical" form={form} onFinish={(values) => saveProfileMutation.mutate(values)}>
                <Form.Item name="first_name" label="First name">
                  <Input />
                </Form.Item>
                <Form.Item name="last_name" label="Last name">
                  <Input />
                </Form.Item>
                <Form.Item name="avatar_url" label="Avatar URL">
                  <Input />
                </Form.Item>
                <Form.Item name="bio" label="Bio">
                  <Input.TextArea rows={4} />
                </Form.Item>
                <Button type="primary" htmlType="submit" loading={saveProfileMutation.isPending}>
                  {meProfileMissing ? 'Создать профиль' : 'Сохранить изменения'}
                </Button>
              </Form>
            ) : (
              <Empty description={extractErrorMessage(meQuery.error)} />
            )}
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card title="Telegram профиль">
            {telegramProfileQuery.isLoading ? (
              <Spin />
            ) : telegramProfileMissing ? (
              <Empty description="Telegram-профиль не привязан" />
            ) : telegramProfileQuery.data ? (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Telegram ID">
                  <Typography.Text code>{telegramProfileQuery.data.telegram_id}</Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label="Username">
                  {telegramProfileQuery.data.telegram_username ?? '-'}
                </Descriptions.Item>
                <Descriptions.Item label="Имя">
                  {[telegramProfileQuery.data.telegram_first_name, telegramProfileQuery.data.telegram_last_name]
                    .filter(Boolean)
                    .join(' ') || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="Создан">{formatDate(telegramProfileQuery.data.created_at)}</Descriptions.Item>
              </Descriptions>
            ) : (
              <Empty description={extractErrorMessage(telegramProfileQuery.error)} />
            )}
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
