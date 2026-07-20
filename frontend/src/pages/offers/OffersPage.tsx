import { useMemo, useState } from 'react';
import { Descriptions, Drawer, Space, Table, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import { CategoryRead, ClassifierService, JobMatcherService, JobOfferAdminRead } from '../../api/generated';
import { formatDate } from '../../utils/formatters';

function normalizeCategories(response: unknown): CategoryRead[] {
  if (Array.isArray(response)) return response as CategoryRead[];
  if (response && typeof response === 'object') {
    const payload = response as { items?: unknown; data?: unknown };
    if (Array.isArray(payload.items)) return payload.items as CategoryRead[];
    if (Array.isArray(payload.data)) return payload.data as CategoryRead[];
  }
  return [];
}

function salaryText(offer: JobOfferAdminRead): string {
  if (!offer.salary_from && !offer.salary_to) return '-';
  return `${offer.salary_from ? `от ${offer.salary_from}` : ''}${
    offer.salary_from && offer.salary_to ? ' ' : ''
  }${offer.salary_to ? `до ${offer.salary_to}` : ''}`;
}

function senderName(offer: JobOfferAdminRead): string {
  return [offer.telegram_first_name, offer.telegram_last_name].filter(Boolean).join(' ');
}

function senderText(offer: JobOfferAdminRead): string {
  const name = senderName(offer);
  const username = offer.telegram_username ? `@${offer.telegram_username}` : '';
  return (
    [name, username].filter(Boolean).join(' · ') || (offer.telegram_sender_id ? `ID ${offer.telegram_sender_id}` : '-')
  );
}

export function OffersPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [selectedOffer, setSelectedOffer] = useState<JobOfferAdminRead | null>(null);

  const offersQuery = useQuery({
    queryKey: ['job-matcher', 'offers', page, pageSize],
    queryFn: () => JobMatcherService.getOffersAdminApiV1PublicJobMatcherOffersGet(undefined, page, pageSize),
  });
  const categoriesQuery = useQuery({
    queryKey: ['categories', 'public'],
    queryFn: () => ClassifierService.getCategoriesApiV1PublicClassifierCategoriesGet(),
    select: normalizeCategories,
  });
  const categoryNames = useMemo(
    () => new Map((categoriesQuery.data ?? []).map((category) => [category.id, category.name])),
    [categoriesQuery.data]
  );

  const columns = [
    {
      title: 'Вакансия',
      render: (_: unknown, offer: JobOfferAdminRead) => (
        <Space direction="vertical" size={2}>
          <Typography.Text strong>{offer.title.slice(0, 120)}</Typography.Text>
          <Typography.Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 0, maxWidth: 480 }}>
            {offer.description ?? '-'}
          </Typography.Paragraph>
        </Space>
      ),
    },
    {
      title: 'Категории',
      render: (_: unknown, offer: JobOfferAdminRead) =>
        offer.category_ids?.length ? (
          <Space size={[0, 4]} wrap>
            {offer.category_ids.map((categoryId) => (
              <Tag color="blue" key={categoryId}>
                {categoryNames.get(categoryId) ?? `${categoryId.slice(0, 8)}…`}
              </Tag>
            ))}
          </Space>
        ) : (
          <Typography.Text type="secondary">Не классифицирована</Typography.Text>
        ),
    },
    { title: 'Локация', dataIndex: 'location', render: (value: string | null) => value ?? '-' },
    { title: 'Зарплата', render: (_: unknown, offer: JobOfferAdminRead) => salaryText(offer) },
    {
      title: 'Контакт',
      render: (_: unknown, offer: JobOfferAdminRead) =>
        offer.telegram_username ? (
          <Typography.Link href={`https://t.me/${offer.telegram_username}`} target="_blank" rel="noreferrer">
            {senderText(offer)}
          </Typography.Link>
        ) : (
          senderText(offer)
        ),
    },
    {
      title: 'Источник',
      render: (_: unknown, offer: JobOfferAdminRead) => (
        <Typography.Text code>{`${offer.source_chat_id}:${offer.source_message_id}`}</Typography.Text>
      ),
    },
    { title: 'Создана', dataIndex: 'created_at', render: (value: string) => formatDate(value) },
  ];

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle title="Offers" subtitle="Сохранённые вакансии из Telegram и результаты их классификации" />
      <Table
        rowKey="id"
        loading={offersQuery.isLoading || categoriesQuery.isLoading}
        columns={columns}
        dataSource={offersQuery.data?.items ?? []}
        onRow={(offer) => ({ onClick: () => setSelectedOffer(offer), style: { cursor: 'pointer' } })}
        pagination={{
          current: page,
          pageSize,
          total: offersQuery.data?.total ?? 0,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100],
          onChange: (nextPage, nextPageSize) => {
            setPage(nextPageSize === pageSize ? nextPage : 1);
            setPageSize(nextPageSize);
          },
        }}
        scroll={{ x: 1200 }}
      />
      <Drawer title="Вакансия" open={selectedOffer !== null} onClose={() => setSelectedOffer(null)} width={720}>
        {selectedOffer ? (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="ID">
              <Typography.Text code copyable>
                {selectedOffer.id}
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Полный текст">
              <Typography.Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                {selectedOffer.description ?? selectedOffer.title}
              </Typography.Paragraph>
            </Descriptions.Item>
            <Descriptions.Item label="Категории">
              {(selectedOffer.category_ids ?? []).map((categoryId) => (
                <Tag color="blue" key={categoryId}>
                  {categoryNames.get(categoryId) ?? categoryId}
                </Tag>
              ))}
            </Descriptions.Item>
            <Descriptions.Item label="Теги">{selectedOffer.tags?.join(', ') || '-'}</Descriptions.Item>
            <Descriptions.Item label="Локация">{selectedOffer.location ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="Зарплата">{salaryText(selectedOffer)}</Descriptions.Item>
            <Descriptions.Item label="Контакт автора">
              {selectedOffer.telegram_username ? (
                <Typography.Link
                  href={`https://t.me/${selectedOffer.telegram_username}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  {senderText(selectedOffer)}
                </Typography.Link>
              ) : (
                senderText(selectedOffer)
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Telegram ID">{selectedOffer.telegram_sender_id ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="Источник">
              {`${selectedOffer.source_chat_id}:${selectedOffer.source_message_id}`}
            </Descriptions.Item>
            <Descriptions.Item label="Создана">{formatDate(selectedOffer.created_at)}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Drawer>
    </Space>
  );
}
