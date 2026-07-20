import { Card, Col, Descriptions, Empty, List, Row, Space, Statistic, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import {
  ClassifierService,
  HealthService,
  MediaService,
  NotificationsService,
  TelegramClientsService,
  UsersService,
} from '../../api/generated';
import { formatDate } from '../../utils/formatters';

export function DashboardPage() {
  const usersQuery = useQuery({
    queryKey: ['dashboard', 'users'],
    queryFn: () => UsersService.getUsersAdminApiV1PublicUsersGet(undefined, 1, 1),
  });
  const mediaQuery = useQuery({
    queryKey: ['dashboard', 'media'],
    queryFn: () => MediaService.listFilesAdminApiV1PublicMediaGet(undefined, 1, 1),
  });
  const telegramQuery = useQuery({
    queryKey: ['dashboard', 'telegram'],
    queryFn: () => TelegramClientsService.getAccountsApiV1PublicTelegramGet(undefined, 1, 1),
  });
  const historyQuery = useQuery({
    queryKey: ['dashboard', 'history'],
    queryFn: () => NotificationsService.getHistoryApiV1PublicNotificationsHistoryGet(undefined, 1, 5),
  });
  const categoriesQuery = useQuery({
    queryKey: ['dashboard', 'categories'],
    queryFn: () => ClassifierService.getCategoriesApiV1PublicClassifierCategoriesGet(),
  });
  const healthQuery = useQuery({
    queryKey: ['dashboard', 'health'],
    queryFn: () => HealthService.healthCheckHealthGet(),
  });

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle title="Dashboard" subtitle="Сводка по живым backend-данным из public API FastAPI" />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} xl={6}>
          <Card>
            <Statistic title="Users" value={usersQuery.data?.total ?? 0} loading={usersQuery.isLoading} />
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card>
            <Statistic title="Media files" value={mediaQuery.data?.total ?? 0} loading={mediaQuery.isLoading} />
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
              title="Categories"
              value={categoriesQuery.data?.length ?? 0}
              loading={categoriesQuery.isLoading}
            />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
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
              <Descriptions.Item label="Transport">
                <Typography.Text>generated fetch client + React Query</Typography.Text>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Последние отправки">
            <List
              loading={historyQuery.isLoading}
              dataSource={historyQuery.data?.items ?? []}
              locale={{ emptyText: <Empty description="История пока пуста" /> }}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    title={`${item.template_name} -> ${item.recipient}`}
                    description={`${item.channel} / ${item.status} / ${formatDate(item.created_at)}`}
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
