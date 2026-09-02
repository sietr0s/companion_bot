import { useState } from 'react';
import { Button, Card, Col, Empty, List, Row, Space, Tag, message } from 'antd';
import { CheckOutlined, PlusOutlined, SettingOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { MarkdownContent } from '../../components/common/MarkdownContent';
import { PageTitle } from '../../components/common/PageTitle';
import { ChatRead, TelegramClientsService } from '../../api/generated';
import { formatDate } from '../../utils/formatters';

export function TelegramChatsPage() {
  const { accountId } = useParams<{ accountId: string }>();
  const navigate = useNavigate();
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null);
  const queryClient = useQueryClient();

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

  const whitelistMutation = useMutation({
    mutationFn: (chatId: number) =>
      TelegramClientsService.addChatToWhitelistApiV1PublicTelegramAccountIdWhitelistPost(accountId!, { chat_id: chatId }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['telegram', 'chats', accountId] });
      void queryClient.invalidateQueries({ queryKey: ['telegram', 'settings', accountId] });
      void message.success('Чат добавлен в whitelist');
    },
  });

  const removeWhitelistMutation = useMutation({
    mutationFn: (chatId: number) =>
      TelegramClientsService.removeChatFromWhitelistApiV1PublicTelegramAccountIdWhitelistChatIdDelete(accountId!, chatId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['telegram', 'chats', accountId] });
      void queryClient.invalidateQueries({ queryKey: ['telegram', 'settings', accountId] });
      void message.success('Чат убран из whitelist');
    },
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
                  <List.Item.Meta title={item.name ?? item.username ?? String(item.id)} description={item.chat_type} />
                  <Button
                    size="small"
                    icon={item.is_in_whitelist ? <CheckOutlined /> : <PlusOutlined />}
                    onClick={(event) => {
                      event.stopPropagation();
                      if (item.is_in_whitelist) removeWhitelistMutation.mutate(item.id);
                      else whitelistMutation.mutate(item.id);
                    }}
                  >
                    {item.is_in_whitelist ? 'Убрать' : 'Добавить'}
                  </Button>
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
                        <MarkdownContent>{item.text}</MarkdownContent>
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
