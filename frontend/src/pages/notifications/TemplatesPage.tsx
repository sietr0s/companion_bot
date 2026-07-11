import { useState } from 'react';
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import { NotificationsService, TemplateRead, TemplateCreate, TemplateUpdate } from '../../api/generated';
import { extractErrorMessage } from '../../utils/api';
import { formatDate } from '../../utils/formatters';

const { TextArea } = Input;

export function TemplatesPage() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<TemplateCreate>();
  const [editingTemplate, setEditingTemplate] = useState<TemplateRead | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateRead | null>(null);

  const templatesQuery = useQuery({
    queryKey: ['notifications', 'templates'],
    queryFn: () => NotificationsService.getTemplatesApiV1PublicNotificationsTemplatesGet(undefined, 1, 100),
  });

  const saveMutation = useMutation({
    mutationFn: (values: TemplateCreate) => {
      if (editingTemplate) {
        return NotificationsService.updateTemplateApiV1PublicNotificationsTemplatesTemplateIdPatch(
          editingTemplate.id,
          values as TemplateUpdate
        );
      }
      return NotificationsService.createTemplateApiV1PublicNotificationsTemplatesPost(values);
    },
    onSuccess: () => {
      setModalOpen(false);
      setEditingTemplate(null);
      form.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['notifications'] });
      void message.success('Шаблон сохранён');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: (templateId: string) =>
      NotificationsService.deleteTemplateApiV1PublicNotificationsTemplatesTemplateIdDelete(templateId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['notifications'] });
      void message.success('Шаблон удалён');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const columns = [
    { title: 'Name', dataIndex: 'name' },
    { title: 'Channel', dataIndex: 'channel', render: (value: string) => <Tag color="blue">{value}</Tag> },
    {
      title: 'Active',
      dataIndex: 'is_active',
      render: (value: boolean) => <Tag color={value ? 'success' : 'default'}>{value ? 'yes' : 'no'}</Tag>,
    },
    { title: 'Created', dataIndex: 'created_at', render: (value: string) => formatDate(value) },
    {
      title: 'Actions',
      render: (_: unknown, record: TemplateRead) => (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setSelectedTemplate(record);
              setDetailsOpen(true);
            }}
          >
            Просмотр
          </Button>
          <Button
            size="small"
            onClick={() => {
              setEditingTemplate(record);
              form.setFieldsValue({
                name: record.name,
                channel: record.channel,
                subject_template: record.subject_template,
                body_template: record.body_template,
                is_active: record.is_active,
              });
              setModalOpen(true);
            }}
          >
            Редактировать
          </Button>
          <Popconfirm title="Удалить шаблон?" onConfirm={() => deleteMutation.mutate(record.id)}>
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
        title="Templates"
        subtitle="Управление шаблонами уведомлений"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingTemplate(null);
              form.setFieldsValue({
                name: '',
                channel: 'email',
                subject_template: '',
                body_template: '',
                is_active: true,
              });
              setModalOpen(true);
            }}
          >
            Новый шаблон
          </Button>
        }
      />
      <Card>
        <Table
          rowKey="id"
          loading={templatesQuery.isLoading}
          columns={columns}
          dataSource={templatesQuery.data?.items ?? []}
          pagination={false}
          scroll={{ x: 900 }}
        />
      </Card>
      <Drawer title="Детали шаблона" open={detailsOpen} onClose={() => setDetailsOpen(false)} width={560}>
        {selectedTemplate ? (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="ID">
              <Typography.Text code>{selectedTemplate.id}</Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Name">{selectedTemplate.name}</Descriptions.Item>
            <Descriptions.Item label="Channel">
              <Tag color="blue">{selectedTemplate.channel}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Subject Template">{selectedTemplate.subject_template}</Descriptions.Item>
            <Descriptions.Item label="Body Template">
              <Typography.Text code>{selectedTemplate.body_template}</Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Active">
              <Tag color={selectedTemplate.is_active ? 'success' : 'default'}>
                {selectedTemplate.is_active ? 'yes' : 'no'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Created">{formatDate(selectedTemplate.created_at)}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Drawer>
      <Modal
        title={editingTemplate ? 'Редактирование шаблона' : 'Создание шаблона'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={saveMutation.isPending}
      >
        <Form
          layout="vertical"
          form={form}
          initialValues={{ is_active: true }}
          onFinish={(values) => saveMutation.mutate(values)}
        >
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="channel" label="Channel" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'email', label: 'Email' },
                { value: 'sms', label: 'SMS' },
                { value: 'push', label: 'Push' },
              ]}
            />
          </Form.Item>
          <Form.Item name="subject_template" label="Subject Template">
            <Input />
          </Form.Item>
          <Form.Item name="body_template" label="Body Template">
            <TextArea rows={6} />
          </Form.Item>
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}
