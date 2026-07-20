import { useMemo, useState } from 'react';
import { Alert, Button, Card, Form, Input, Modal, Popconfirm, Space, Table, Tag, Typography, message } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import {
  CategoryRead,
  ClassifierService,
  JobMatcherService,
  SubscriptionAdminRead,
  UsersService,
  src__modules__users__schemas__public__user__UserRead as UserRead,
} from '../../api/generated';
import { formatDate } from '../../utils/formatters';
import { extractErrorMessage } from '../../utils/api';

function normalizeCategories(response: unknown): CategoryRead[] {
  if (Array.isArray(response)) return response as CategoryRead[];
  if (response && typeof response === 'object') {
    const payload = response as { items?: unknown; data?: unknown };
    if (Array.isArray(payload.items)) return payload.items as CategoryRead[];
    if (Array.isArray(payload.data)) return payload.data as CategoryRead[];
  }
  return [];
}

export function UsersPage() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<{
    first_name?: string;
    last_name?: string;
    avatar_url?: string;
    bio?: string;
  }>();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [editingUser, setEditingUser] = useState<UserRead | null>(null);

  const updateMutation = useMutation({
    mutationFn: (values: { first_name?: string; last_name?: string; avatar_url?: string; bio?: string }) => {
      if (!editingUser) throw new Error('Пользователь не выбран');
      return UsersService.updateUserAdminApiV1PublicUsersProfileIdPatch(editingUser.id, values);
    },
    onSuccess: () => {
      setEditingUser(null);
      form.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['users'] });
      void message.success('Пользователь обновлён');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: (authId: string) => JobMatcherService.deleteUserAdminApiV1PublicJobMatcherUsersAuthIdDelete(authId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['users'] });
      void message.success('Пользователь, учётная запись и подписка удалены');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const usersQuery = useQuery({
    queryKey: ['users', 'all', page, pageSize],
    queryFn: () => UsersService.getUsersAdminApiV1PublicUsersGet(undefined, page, pageSize),
  });
  const subscriptionsQuery = useQuery({
    queryKey: ['job-matcher', 'subscriptions'],
    queryFn: () => JobMatcherService.getSubscriptionsAdminApiV1PublicJobMatcherSubscriptionsGet(undefined, 1, 500),
  });
  const categoriesQuery = useQuery({
    queryKey: ['categories', 'public'],
    queryFn: () => ClassifierService.getCategoriesApiV1PublicClassifierCategoriesGet(),
    select: normalizeCategories,
  });

  const subscriptionsByAuthId = useMemo(
    () =>
      new Map<string, SubscriptionAdminRead>(
        (subscriptionsQuery.data?.items ?? []).map((subscription) => [subscription.auth_id, subscription])
      ),
    [subscriptionsQuery.data?.items]
  );
  const categoryNamesById = useMemo(
    () => new Map((categoriesQuery.data ?? []).map((category) => [category.id, category.name])),
    [categoriesQuery.data]
  );

  const columns = [
    {
      title: 'Пользователь',
      render: (_: unknown, record: UserRead) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>
            {[record.first_name, record.last_name].filter(Boolean).join(' ') || 'Без имени'}
          </Typography.Text>
          <Typography.Text type="secondary">Создан {formatDate(record.created_at)}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Auth ID',
      dataIndex: 'auth_id',
      render: (value: string) => (
        <Typography.Text code copyable={{ text: value }}>
          {value.slice(0, 8)}…
        </Typography.Text>
      ),
    },
    {
      title: 'Категории подписки',
      render: (_: unknown, record: UserRead) => {
        const subscription = subscriptionsByAuthId.get(record.auth_id);
        if (!subscription?.category_ids?.length) {
          return <Typography.Text type="secondary">Нет подписки</Typography.Text>;
        }
        return (
          <Space size={[0, 4]} wrap>
            {subscription.category_ids.map((categoryId) => (
              <Tag color="blue" key={categoryId}>
                {categoryNamesById.get(categoryId) ?? `${categoryId.slice(0, 8)}…`}
              </Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: 'Условия',
      render: (_: unknown, record: UserRead) => {
        const subscription = subscriptionsByAuthId.get(record.auth_id);
        if (!subscription) return '-';
        const salary =
          subscription.min_salary || subscription.max_salary
            ? `${subscription.min_salary ? `от ${subscription.min_salary}` : ''}${
                subscription.min_salary && subscription.max_salary ? ' ' : ''
              }${subscription.max_salary ? `до ${subscription.max_salary}` : ''}`
            : null;
        return (
          <Space direction="vertical" size={2}>
            {subscription.keywords?.length ? (
              <Typography.Text>Ключевые слова: {subscription.keywords.join(', ')}</Typography.Text>
            ) : null}
            {salary ? <Typography.Text>Зарплата: {salary}</Typography.Text> : null}
            {subscription.locations?.length ? (
              <Typography.Text>Локации: {subscription.locations.join(', ')}</Typography.Text>
            ) : null}
            {!subscription.keywords?.length && !salary && !subscription.locations?.length ? '-' : null}
          </Space>
        );
      },
    },
    {
      title: 'Статус',
      render: (_: unknown, record: UserRead) => {
        const subscription = subscriptionsByAuthId.get(record.auth_id);
        if (!subscription) return <Tag>Нет</Tag>;
        return (
          <Tag color={subscription.is_active ? 'green' : 'default'}>
            {subscription.is_active ? 'Активна' : 'Отключена'}
          </Tag>
        );
      },
    },
    {
      title: 'Обновлена',
      render: (_: unknown, record: UserRead) => {
        const subscription = subscriptionsByAuthId.get(record.auth_id);
        return subscription ? formatDate(subscription.updated_at) : '-';
      },
    },
    {
      title: 'Действия',
      fixed: 'right' as const,
      render: (_: unknown, record: UserRead) => (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setEditingUser(record);
              form.setFieldsValue({
                first_name: record.first_name ?? '',
                last_name: record.last_name ?? '',
                avatar_url: record.avatar_url ?? '',
                bio: record.bio ?? '',
              });
            }}
          >
            Редактировать
          </Button>
          <Popconfirm
            title="Удалить пользователя?"
            description="Будут удалены профиль пользователя, учётная запись auth и подписка."
            okText="Удалить"
            cancelText="Отмена"
            okButtonProps={{ danger: true }}
            onConfirm={() => deleteMutation.mutate(record.auth_id)}
          >
            <Button size="small" danger loading={deleteMutation.isPending}>
              Удалить
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle title="Пользователи" subtitle="Пользователи, категории и параметры их подписок на вакансии" />
      {subscriptionsQuery.isError ? (
        <Alert
          type="error"
          showIcon
          message="Не удалось загрузить подписки"
          description={extractErrorMessage(subscriptionsQuery.error)}
        />
      ) : null}
      <Card title={`Пользователи и подписки (${usersQuery.data?.total ?? 0})`}>
        <Table
          rowKey="id"
          loading={usersQuery.isLoading || subscriptionsQuery.isLoading || categoriesQuery.isLoading}
          columns={columns}
          dataSource={usersQuery.data?.items ?? []}
          pagination={{
            current: page,
            pageSize,
            total: usersQuery.data?.total ?? 0,
            showSizeChanger: true,
            pageSizeOptions: [20, 50, 100],
            onChange: (nextPage, nextPageSize) => {
              setPage(nextPageSize === pageSize ? nextPage : 1);
              setPageSize(nextPageSize);
            },
          }}
          scroll={{ x: 1200 }}
        />
      </Card>
      <Modal
        title="Редактирование пользователя"
        open={editingUser !== null}
        onCancel={() => {
          setEditingUser(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={updateMutation.isPending}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <Form layout="vertical" form={form} onFinish={(values) => updateMutation.mutate(values)}>
          <Form.Item name="first_name" label="Имя">
            <Input maxLength={100} />
          </Form.Item>
          <Form.Item name="last_name" label="Фамилия">
            <Input maxLength={100} />
          </Form.Item>
          <Form.Item name="avatar_url" label="URL аватара">
            <Input maxLength={500} />
          </Form.Item>
          <Form.Item name="bio" label="О пользователе">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}
