import { useState } from 'react';
import { Button, Card, Descriptions, Drawer, Empty, List, Space, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import { NotificationsService, NotificationLogRead } from '../../api/generated';
import { formatDate } from '../../utils/formatters';

export function HistoryPage() {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedLog, setSelectedLog] = useState<NotificationLogRead | null>(null);

  const historyQuery = useQuery({
    queryKey: ['notifications', 'history'],
    queryFn: () => NotificationsService.getHistoryApiV1PublicNotificationsHistoryGet(undefined, 1, 100),
  });

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle title="History" subtitle="История отправленных уведомлений" />
      <Card>
        <List
          loading={historyQuery.isLoading}
          dataSource={historyQuery.data?.items ?? []}
          locale={{ emptyText: <Empty description="История пока пуста" /> }}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Button
                  key="view"
                  size="small"
                  onClick={() => {
                    setSelectedLog(item);
                    setDetailsOpen(true);
                  }}
                >
                  Просмотр
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={`${item.template_name} -> ${item.recipient}`}
                description={
                  <Space>
                    <Tag color="blue">{item.channel}</Tag>
                    <Tag color={item.status === 'success' ? 'success' : 'error'}>{item.status}</Tag>
                    <Typography.Text type="secondary">{formatDate(item.created_at)}</Typography.Text>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Card>
      <Drawer title="Детали отправки" open={detailsOpen} onClose={() => setDetailsOpen(false)} width={560}>
        {selectedLog ? (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="ID">
              <Typography.Text code>{selectedLog.id}</Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Template Name">{selectedLog.template_name}</Descriptions.Item>
            <Descriptions.Item label="Recipient">{selectedLog.recipient}</Descriptions.Item>
            <Descriptions.Item label="Channel">
              <Tag color="blue">{selectedLog.channel}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={selectedLog.status === 'success' ? 'success' : 'error'}>{selectedLog.status}</Tag>
            </Descriptions.Item>
            {selectedLog.error_message ? (
              <Descriptions.Item label="Error">
                <Typography.Text type="danger">{selectedLog.error_message}</Typography.Text>
              </Descriptions.Item>
            ) : null}
            <Descriptions.Item label="Created">{formatDate(selectedLog.created_at)}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Drawer>
    </Space>
  );
}
