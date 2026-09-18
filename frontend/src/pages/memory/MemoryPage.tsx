import { useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Collapse,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MarkdownContent } from '../../components/common/MarkdownContent';
import { PageTitle } from '../../components/common/PageTitle';
import {
  ConversationCreate,
  ConversationRead,
  MemoryMessageCreate,
  MemoryMessageRead,
  MemoryService,
  SummaryStateCreate,
  SummaryStateRead,
  UserRead,
  UsersService,
  VectorTopicRead,
} from '../../api/generated';
import { formatDate } from '../../utils/formatters';
import { extractErrorMessage } from '../../utils/api';

function statusColor(status: string) {
  if (status === 'active') return 'green';
  if (status === 'paused' || status === 'archived') return 'orange';
  return 'default';
}

function userTitle(user: UserRead | undefined, conversation: ConversationRead) {
  if (!user) {
    return conversation.user_id ? `User ${conversation.user_id.slice(0, 8)}…` : `Chat ${conversation.telegram_chat_id}`;
  }
  const name = [user.first_name, user.last_name].filter(Boolean).join(' ');
  if (name) return name;
  if (user.username) return `@${user.username}`;
  return `${user.platform} ${user.platform_user_id}`;
}

function MemoryBubbles({ messages }: { messages: MemoryMessageRead[] }) {
  if (messages.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Нет сообщений" />;
  }
  return (
    <div className="memory-thread">
      {messages.map((item) => {
        const outgoing = item.direction === 'outgoing' || item.direction === 'out';
        return (
          <div key={item.id} className={outgoing ? 'memory-bubble-row out' : 'memory-bubble-row in'}>
            <div className={outgoing ? 'memory-bubble out' : 'memory-bubble in'}>
              <div className="memory-bubble-meta">
                <span>{outgoing ? 'Бот' : 'Пользователь'}</span>
                <span>#{item.sequence_number}</span>
                <span>{formatDate(item.created_at)}</span>
                {item.message_type !== 'text' ? <Tag>{item.message_type}</Tag> : null}
              </div>
              <MarkdownContent className="memory-bubble-text">{item.text}</MarkdownContent>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function MemoryPage() {
  const queryClient = useQueryClient();
  const [conversationForm] = Form.useForm<ConversationCreate>();
  const [messageForm] = Form.useForm<MemoryMessageCreate>();
  const [summaryForm] = Form.useForm<SummaryStateCreate>();
  const [conversationOpen, setConversationOpen] = useState(false);
  const [messageOpen, setMessageOpen] = useState(false);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const conversationsQuery = useQuery({
    queryKey: ['memory', 'conversations'],
    queryFn: () => MemoryService.getListApiV1PublicMemoryConversationsGet(1, 100, '-last_activity_at'),
  });
  const messagesQuery = useQuery({
    queryKey: ['memory', 'messages'],
    queryFn: () => MemoryService.getListApiV1PublicMemoryMessagesGet(1, 200, 'sequence_number'),
  });
  const summariesQuery = useQuery({
    queryKey: ['memory', 'summaries'],
    queryFn: () => MemoryService.getListApiV1PublicMemorySummaryStatesGet(1, 100),
  });
  const topicsQuery = useQuery({
    queryKey: ['memory', 'topics', selectedId],
    queryFn: () =>
      MemoryService.listConversationTopicsApiV1PublicMemoryConversationsConversationIdTopicsGet(
        selectedId as string,
      ),
    enabled: Boolean(selectedId),
  });
  const topicDetailQuery = useQuery({
    queryKey: ['memory', 'topics', selectedId, selectedTopicId],
    queryFn: () =>
      MemoryService.getConversationTopicApiV1PublicMemoryConversationsConversationIdTopicsTopicIdGet(
        selectedId as string,
        selectedTopicId as string,
      ),
    enabled: Boolean(selectedId && selectedTopicId),
  });
  const usersQuery = useQuery({
    queryKey: ['users', 'memory-lookup'],
    queryFn: () => UsersService.getListApiV1PublicUsersGet(1, 200),
  });

  const usersById = useMemo(() => {
    const map = new Map<string, UserRead>();
    for (const user of usersQuery.data?.items ?? []) {
      map.set(user.id, user);
    }
    return map;
  }, [usersQuery.data]);

  const conversations = useMemo(() => {
    const items = [...(conversationsQuery.data?.items ?? [])];
    items.sort(
      (a, b) => new Date(b.last_activity_at).getTime() - new Date(a.last_activity_at).getTime(),
    );
    const query = search.trim().toLowerCase();
    if (!query) return items;
    return items.filter((item) => {
      const user = item.user_id ? usersById.get(item.user_id) : undefined;
      const haystack = [
        String(item.telegram_chat_id),
        item.status,
        item.id,
        item.user_id ?? '',
        userTitle(user, item),
        user?.username ?? '',
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [conversationsQuery.data, search, usersById]);

  const selected = conversations.find((item) => item.id === selectedId) ?? null;

  const threadMessages = useMemo(() => {
    if (!selectedId) return [];
    return (messagesQuery.data?.items ?? [])
      .filter((item) => item.conversation_id === selectedId)
      .sort((a, b) => a.sequence_number - b.sequence_number);
  }, [messagesQuery.data, selectedId]);

  const threadSummary = useMemo(
    () => (summariesQuery.data?.items ?? []).find((item) => item.conversation_id === selectedId) ?? null,
    [summariesQuery.data, selectedId],
  );

  const threadTopics = topicsQuery.data ?? [];

  const createConversation = useMutation({
    mutationFn: (values: ConversationCreate) =>
      MemoryService.createApiV1PublicMemoryConversationsPost({
        ...values,
        telegram_chat_id: Number(values.telegram_chat_id),
      }),
    onSuccess: (created) => {
      setConversationOpen(false);
      conversationForm.resetFields();
      setSelectedId(created.id);
      void queryClient.invalidateQueries({ queryKey: ['memory', 'conversations'] });
      void message.success('Диалог создан');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });
  const deleteConversation = useMutation({
    mutationFn: (id: string) => MemoryService.deleteApiV1PublicMemoryConversationsItemIdDelete(id),
    onSuccess: (_data, id) => {
      if (selectedId === id) setSelectedId(null);
      void queryClient.invalidateQueries({ queryKey: ['memory'] });
      void message.success('Диалог удалён');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const createMessage = useMutation({
    mutationFn: (values: MemoryMessageCreate) =>
      MemoryService.createApiV1PublicMemoryMessagesPost({
        ...values,
        sequence_number: Number(values.sequence_number),
      }),
    onSuccess: () => {
      setMessageOpen(false);
      messageForm.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['memory', 'messages'] });
      void queryClient.invalidateQueries({ queryKey: ['memory', 'conversations'] });
      void message.success('Сообщение создано');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });
  const deleteMessage = useMutation({
    mutationFn: (id: string) => MemoryService.deleteApiV1PublicMemoryMessagesItemIdDelete(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['memory', 'messages'] });
      void message.success('Сообщение удалено');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const createSummary = useMutation({
    mutationFn: (values: SummaryStateCreate) =>
      MemoryService.createApiV1PublicMemorySummaryStatesPost({
        ...values,
        checkpoint: Number(values.checkpoint ?? 0),
      }),
    onSuccess: () => {
      setSummaryOpen(false);
      summaryForm.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['memory', 'summaries'] });
      void message.success('Summary создан');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });
  const deleteSummary = useMutation({
    mutationFn: (id: string) => MemoryService.deleteApiV1PublicMemorySummaryStatesItemIdDelete(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['memory', 'summaries'] });
      void message.success('Summary удалён');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const deleteTopic = useMutation({
    mutationFn: (id: string) => MemoryService.deleteApiV1PublicMemoryVectorRecordsItemIdDelete(id),
    onSuccess: (_data, id) => {
      if (selectedTopicId === id) setSelectedTopicId(null);
      void queryClient.invalidateQueries({ queryKey: ['memory', 'topics'] });
      void message.success('Тема удалена');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const openMessageModal = () => {
    if (!selected) return;
    const lastMessage = threadMessages[threadMessages.length - 1];
    const nextSeq = (lastMessage?.sequence_number ?? selected.last_sequence_number ?? 0) + 1;
    messageForm.setFieldsValue({
      conversation_id: selected.id,
      direction: 'in',
      message_type: 'text',
      sequence_number: nextSeq,
    });
    setMessageOpen(true);
  };

  const openSummaryModal = () => {
    if (!selected) return;
    summaryForm.setFieldsValue({
      conversation_id: selected.id,
      checkpoint: selected.last_sequence_number,
    });
    setSummaryOpen(true);
  };

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle title="Memory" subtitle="Диалоги бота: чаты слева, переписка и память справа" />
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={8}>
          <Card
            title={`Диалоги (${conversationsQuery.data?.total ?? 0})`}
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setConversationOpen(true)}>
                Новый
              </Button>
            }
          >
            <Input.Search
              allowClear
              placeholder="Поиск по chat id, имени, статусу"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              style={{ marginBottom: 12 }}
            />
            <List
              loading={conversationsQuery.isLoading}
              dataSource={conversations}
              locale={{ emptyText: <Empty description="Нет диалогов" /> }}
              renderItem={(item: ConversationRead) => {
                const user = item.user_id ? usersById.get(item.user_id) : undefined;
                return (
                  <List.Item
                    className={selectedId === item.id ? 'chat-row active' : 'chat-row'}
                    onClick={() => {
                      setSelectedId(item.id);
                      setSelectedTopicId(null);
                    }}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Typography.Text strong>{userTitle(user, item)}</Typography.Text>
                          <Tag color={statusColor(item.status)}>{item.status}</Tag>
                        </Space>
                      }
                      description={
                        <Space direction="vertical" size={0}>
                          <Typography.Text type="secondary">chat {item.telegram_chat_id}</Typography.Text>
                          <Typography.Text type="secondary">{formatDate(item.last_activity_at)}</Typography.Text>
                        </Space>
                      }
                    />
                    <Typography.Text type="secondary">#{item.last_sequence_number}</Typography.Text>
                  </List.Item>
                );
              }}
            />
          </Card>
        </Col>
        <Col xs={24} xl={16}>
          {!selected ? (
            <Card>
              <Empty description="Выберите диалог слева" />
            </Card>
          ) : (
            <Space direction="vertical" size="middle" className="page-stack">
              <Card
                title={
                  <Space wrap>
                    <Typography.Text strong>
                      {userTitle(selected.user_id ? usersById.get(selected.user_id) : undefined, selected)}
                    </Typography.Text>
                    <Tag color={statusColor(selected.status)}>{selected.status}</Tag>
                    <Typography.Text type="secondary">chat {selected.telegram_chat_id}</Typography.Text>
                  </Space>
                }
                extra={
                  <Space>
                    <Button onClick={openMessageModal}>Сообщение</Button>
                    <Popconfirm
                      title="Удалить диалог и связанную память?"
                      onConfirm={() => deleteConversation.mutate(selected.id)}
                    >
                      <Button danger>Удалить</Button>
                    </Popconfirm>
                  </Space>
                }
              >
                <Typography.Text type="secondary">
                  Активность {formatDate(selected.last_activity_at)} · seq {selected.last_sequence_number}
                </Typography.Text>
              </Card>

              <Collapse
                items={[
                  {
                    key: 'summary',
                    label: threadSummary ? `Summary · checkpoint ${threadSummary.checkpoint}` : 'Summary',
                    extra: threadSummary ? (
                      <Popconfirm
                        title="Удалить summary?"
                        onConfirm={(event) => {
                          event?.stopPropagation();
                          deleteSummary.mutate(threadSummary.id);
                        }}
                      >
                        <Button size="small" danger onClick={(event) => event.stopPropagation()}>
                          Удалить
                        </Button>
                      </Popconfirm>
                    ) : (
                      <Button
                        size="small"
                        onClick={(event) => {
                          event.stopPropagation();
                          openSummaryModal();
                        }}
                      >
                        Добавить
                      </Button>
                    ),
                    children: threadSummary?.current_summary ? (
                      <MarkdownContent>{threadSummary.current_summary}</MarkdownContent>
                    ) : (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Нет summary" />
                    ),
                  },
                ]}
              />

              <Card title={`Сообщения (${threadMessages.length})`} loading={messagesQuery.isLoading}>
                {threadMessages.length === 0 ? (
                  <Empty description="В этом диалоге пока нет сообщений" />
                ) : (
                  <div className="memory-thread">
                    {threadMessages.map((item: MemoryMessageRead) => {
                      const outgoing = item.direction === 'out';
                      return (
                        <div
                          key={item.id}
                          className={outgoing ? 'memory-bubble-row out' : 'memory-bubble-row in'}
                        >
                          <div className={outgoing ? 'memory-bubble out' : 'memory-bubble in'}>
                            <div className="memory-bubble-meta">
                              <span>{outgoing ? 'Бот' : 'Пользователь'}</span>
                              <span>#{item.sequence_number}</span>
                              <span>{formatDate(item.created_at)}</span>
                              {item.message_type !== 'text' ? <Tag>{item.message_type}</Tag> : null}
                            </div>
                            <MarkdownContent className="memory-bubble-text">{item.text}</MarkdownContent>
                            <Popconfirm
                              title="Удалить сообщение?"
                              onConfirm={() => deleteMessage.mutate(item.id)}
                            >
                              <Button size="small" type="link" danger>
                                Удалить
                              </Button>
                            </Popconfirm>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>

              <Card title={`Темы (${threadTopics.length})`} loading={topicsQuery.isLoading}>
                {threadTopics.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Нет закрытых тем" />
                ) : (
                  <List
                    dataSource={threadTopics}
                    renderItem={(item: VectorTopicRead) => (
                      <List.Item
                        className={item.id === selectedTopicId ? 'chat-row active' : 'chat-row'}
                        onClick={() => setSelectedTopicId(item.id)}
                        actions={[
                          <Popconfirm
                            key="delete"
                            title="Удалить тему?"
                            onConfirm={(event) => {
                              event?.stopPropagation();
                              deleteTopic.mutate(item.id);
                            }}
                          >
                            <Button size="small" danger onClick={(event) => event.stopPropagation()}>
                              Удалить
                            </Button>
                          </Popconfirm>,
                        ]}
                      >
                        <List.Item.Meta
                          title={item.title}
                          description={
                            <Space wrap size={8}>
                              <Typography.Text type="secondary">
                                #{item.seq_from}–{item.seq_to}
                              </Typography.Text>
                              <Typography.Text type="secondary">{item.message_count} сообщ.</Typography.Text>
                              {item.partial ? <Tag color="orange">partial</Tag> : null}
                              <Typography.Text type="secondary">{formatDate(item.created_at)}</Typography.Text>
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                  />
                )}
              </Card>
            </Space>
          )}
        </Col>
      </Row>

      <Modal
        title="Новый диалог"
        open={conversationOpen}
        onCancel={() => setConversationOpen(false)}
        onOk={() => conversationForm.submit()}
        confirmLoading={createConversation.isPending}
      >
        <Form layout="vertical" form={conversationForm} onFinish={(values) => createConversation.mutate(values)}>
          <Form.Item name="telegram_chat_id" label="Telegram chat ID" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="user_id" label="User ID">
            <Input />
          </Form.Item>
          <Form.Item name="telegram_account_id" label="Telegram account ID">
            <Input />
          </Form.Item>
          <Form.Item name="status" label="Status" initialValue="active">
            <Select
              options={[
                { value: 'active', label: 'active' },
                { value: 'paused', label: 'paused' },
                { value: 'archived', label: 'archived' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Новое сообщение"
        open={messageOpen}
        onCancel={() => setMessageOpen(false)}
        onOk={() => messageForm.submit()}
        confirmLoading={createMessage.isPending}
      >
        <Form layout="vertical" form={messageForm} onFinish={(values) => createMessage.mutate(values)}>
          <Form.Item name="conversation_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item name="text" label="Текст" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="direction" label="Направление" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'in', label: 'Входящее (пользователь)' },
                { value: 'out', label: 'Исходящее (бот)' },
              ]}
            />
          </Form.Item>
          <Form.Item name="message_type" label="Тип" initialValue="text">
            <Input />
          </Form.Item>
          <Form.Item name="sequence_number" label="Sequence" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Новый summary"
        open={summaryOpen}
        onCancel={() => setSummaryOpen(false)}
        onOk={() => summaryForm.submit()}
        confirmLoading={createSummary.isPending}
      >
        <Form layout="vertical" form={summaryForm} onFinish={(values) => createSummary.mutate(values)}>
          <Form.Item name="conversation_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item name="current_summary" label="Summary">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="checkpoint" label="Checkpoint" initialValue={0}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={topicDetailQuery.data?.title ?? 'Тема'}
        open={Boolean(selectedTopicId)}
        onClose={() => setSelectedTopicId(null)}
        width={480}
      >
        {topicDetailQuery.data ? (
          <Space direction="vertical" size="middle" className="page-stack">
            <Typography.Text type="secondary">
              #{topicDetailQuery.data.seq_from}–{topicDetailQuery.data.seq_to}
              {topicDetailQuery.data.partial ? ' · partial' : ''}
            </Typography.Text>
            <MemoryBubbles messages={topicDetailQuery.data.messages ?? []} />
          </Space>
        ) : (
          <Empty description="Загрузка…" />
        )}
      </Drawer>
    </Space>
  );
}
