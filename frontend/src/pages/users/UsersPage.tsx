import { useState } from 'react';
import { Button, Card, Form, Input, Modal, Popconfirm, Space, Table, Typography, message } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import { UserCreate, UserRead, UserUpdate, UsersService } from '../../api/generated';
import { formatDate } from '../../utils/formatters';
import { extractErrorMessage } from '../../utils/api';

export function UsersPage() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<UserCreate & UserUpdate>();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [editingUser, setEditingUser] = useState<UserRead | null>(null);
  const [creating, setCreating] = useState(false);

  const usersQuery = useQuery({
    queryKey: ['users', page, pageSize],
    queryFn: () => UsersService.getListApiV1PublicUsersGet(page, pageSize),
  });

  const saveMutation = useMutation({
    mutationFn: (values: UserCreate & UserUpdate) => {
      if (editingUser) {
        return UsersService.updateApiV1PublicUsersItemIdPut(editingUser.id, values);
      }
      return UsersService.createApiV1PublicUsersPost({
        platform: values.platform,
        platform_user_id: values.platform_user_id,
        username: values.username,
        first_name: values.first_name,
        last_name: values.last_name,
        notes: values.notes,
      });
    },
    onSuccess: () => {
      setEditingUser(null);
      setCreating(false);
      form.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['users'] });
      void message.success(editingUser ? 'Пользователь обновлён' : 'Пользователь создан');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => UsersService.deleteApiV1PublicUsersItemIdDelete(userId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['users'] });
      void message.success('Пользователь удалён');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const columns = [
    {
      title: 'Имя',
      render: (_: unknown, record: UserRead) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>
            {[record.first_name, record.last_name].filter(Boolean).join(' ') || 'Без имени'}
          </Typography.Text>
          <Typography.Text type="secondary">{record.username ? `@${record.username}` : 'без username'}</Typography.Text>
        </Space>
      ),
    },
    { title: 'Канал', dataIndex: 'platform' },
    { title: 'ID', dataIndex: 'platform_user_id' },
    { title: 'Заметки', dataIndex: 'notes', ellipsis: true },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      render: (value: string | null | undefined) => (value ? formatDate(value) : '—'),
    },
    {
      title: 'Действия',
      render: (_: unknown, record: UserRead) => (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setCreating(false);
              setEditingUser(record);
              form.setFieldsValue({
                platform: record.platform,
                platform_user_id: record.platform_user_id,
                username: record.username ?? undefined,
                first_name: record.first_name ?? undefined,
                last_name: record.last_name ?? undefined,
                notes: record.notes ?? undefined,
              });
            }}
          >
            Редактировать
          </Button>
          <Popconfirm title="Удалить пользователя?" onConfirm={() => deleteMutation.mutate(record.id)}>
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
      <PageTitle
        title="Собеседники"
        subtitle="Собеседники по каналу (telegram / instagram)"
        extra={
          <Button
            type="primary"
            onClick={() => {
              setEditingUser(null);
              setCreating(true);
              form.resetFields();
            }}
          >
            Добавить
          </Button>
        }
      />
      <Card title={`Пользователи (${usersQuery.data?.total ?? 0})`}>
        <Table
          rowKey="id"
          loading={usersQuery.isLoading}
          columns={columns}
          dataSource={usersQuery.data?.items ?? []}
          pagination={{
            current: page,
            pageSize,
            total: usersQuery.data?.total ?? 0,
            showSizeChanger: true,
            onChange: (nextPage, nextPageSize) => {
              setPage(nextPageSize === pageSize ? nextPage : 1);
              setPageSize(nextPageSize);
            },
          }}
        />
      </Card>
      <Modal
        title={editingUser ? 'Редактирование пользователя' : 'Новый пользователь'}
        open={creating || editingUser !== null}
        onCancel={() => {
          setEditingUser(null);
          setCreating(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={saveMutation.isPending}
        okText="Сохранить"
      >
        <Form layout="vertical" form={form} onFinish={(values) => saveMutation.mutate(values)}>
          <Form.Item name="platform" label="Канал" rules={[{ required: !editingUser, message: 'Укажите platform' }]}>
            <Input placeholder="telegram или instagram" disabled={Boolean(editingUser)} />
          </Form.Item>
          <Form.Item
            name="platform_user_id"
            label="ID на канале"
            rules={[{ required: !editingUser, message: 'Укажите platform_user_id' }]}
          >
            <Input disabled={Boolean(editingUser)} />
          </Form.Item>
          <Form.Item name="username" label="Username">
            <Input maxLength={100} />
          </Form.Item>
          <Form.Item name="first_name" label="Имя">
            <Input maxLength={100} />
          </Form.Item>
          <Form.Item name="last_name" label="Фамилия">
            <Input maxLength={100} />
          </Form.Item>
          <Form.Item name="notes" label="Заметки">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}
