import { Card, Col, Descriptions, Row, Space, Statistic, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import { HealthService, MemoryService, TelegramClientsService, UsersService } from '../../api/generated';

export function DashboardPage() {
  const usersQuery = useQuery({
    queryKey: ['dashboard', 'users'],
    queryFn: () => UsersService.getListApiV1PublicUsersGet(1, 1),
  });
  const telegramQuery = useQuery({
    queryKey: ['dashboard', 'telegram'],
    queryFn: () => TelegramClientsService.getAccountsApiV1PublicTelegramGet(undefined, 1, 1),
  });
  const conversationsQuery = useQuery({
    queryKey: ['dashboard', 'conversations'],
    queryFn: () => MemoryService.getListApiV1PublicMemoryConversationsGet(1, 1),
  });
  const healthQuery = useQuery({
    queryKey: ['dashboard', 'health'],
    queryFn: () => HealthService.healthCheckHealthGet(),
  });

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle title="Dashboard" subtitle="Сводка по публичному API companion_bot" />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} xl={6}>
          <Card>
            <Statistic title="Users" value={usersQuery.data?.total ?? 0} loading={usersQuery.isLoading} />
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card>
            <Statistic
              title="Telegram accounts"
              value={telegramQuery.data?.total ?? 0}
              loading={telegramQuery.isLoading}
            />
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card>
            <Statistic
              title="Conversations"
              value={conversationsQuery.data?.total ?? 0}
              loading={conversationsQuery.isLoading}
            />
          </Card>
        </Col>
      </Row>
      <Card title="Health">
        <Descriptions column={1} size="small">
          <Descriptions.Item label="Backend status">
            <Tag color={healthQuery.data?.status === 'ok' ? 'success' : 'default'}>
              {healthQuery.data?.status ?? 'unknown'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="API source">
            <Typography.Text code>frontend/openapi.json</Typography.Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  );
}
