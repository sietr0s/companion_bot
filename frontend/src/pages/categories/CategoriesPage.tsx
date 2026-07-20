import { useState } from 'react';
import { Button, Card, Form, Input, Modal, Popconfirm, Space, Switch, Table, Tag, Typography, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import { CategoryRead, ClassifierService } from '../../api/generated';
import { extractErrorMessage } from '../../utils/api';
import { slugify } from '../../utils/formatters';

export function CategoriesPage() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<{ name: string; slug: string; description?: string; is_active: boolean }>();
  const [editingCategory, setEditingCategory] = useState<CategoryRead | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const categoriesQuery = useQuery({
    queryKey: ['categories'],
    queryFn: () => ClassifierService.getCategoriesApiV1PublicClassifierCategoriesGet(),
  });

  const saveMutation = useMutation({
    mutationFn: (values: { name: string; slug: string; description?: string; is_active: boolean }) => {
      if (editingCategory) {
        return ClassifierService.updateCategoryApiV1PublicClassifierCategoriesSlugPatch(editingCategory.slug, {
          name: values.name,
          description: values.description,
          is_active: values.is_active,
        });
      }
      return ClassifierService.createCategoryApiV1PublicClassifierCategoriesPost(values);
    },
    onSuccess: () => {
      setModalOpen(false);
      setEditingCategory(null);
      form.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['categories'] });
      void message.success('Категория сохранена');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: (slug: string) => ClassifierService.deleteCategoryApiV1PublicClassifierCategoriesSlugDelete(slug),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['categories'] });
      void message.success('Категория удалена');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle
        title="Categories"
        subtitle="Категории классификатора с авто-генерацией slug в форме"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingCategory(null);
              form.setFieldsValue({ name: '', slug: '', description: '', is_active: true });
              setModalOpen(true);
            }}
          >
            Новая категория
          </Button>
        }
      />
      <Card>
        <Table
          rowKey="id"
          loading={categoriesQuery.isLoading}
          dataSource={categoriesQuery.data ?? []}
          pagination={false}
          columns={[
            { title: 'Name', dataIndex: 'name' },
            {
              title: 'Slug',
              dataIndex: 'slug',
              render: (value: string) => <Typography.Text code>{value}</Typography.Text>,
            },
            { title: 'Description', dataIndex: 'description', render: (value: string | null) => value ?? '-' },
            {
              title: 'Active',
              dataIndex: 'is_active',
              render: (value: boolean) => (
                <Tag color={value ? 'success' : 'default'}>{value ? 'active' : 'inactive'}</Tag>
              ),
            },
            {
              title: 'Actions',
              render: (_: unknown, record: CategoryRead) => (
                <Space>
                  <Button
                    size="small"
                    onClick={() => {
                      setEditingCategory(record);
                      form.setFieldsValue({
                        name: record.name,
                        slug: record.slug,
                        description: record.description ?? '',
                        is_active: record.is_active,
                      });
                      setModalOpen(true);
                    }}
                  >
                    Редактировать
                  </Button>
                  <Popconfirm title="Удалить категорию?" onConfirm={() => deleteMutation.mutate(record.slug)}>
                    <Button size="small" danger>
                      Удалить
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        title={editingCategory ? 'Редактирование категории' : 'Создание категории'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={saveMutation.isPending}
      >
        <Form
          layout="vertical"
          form={form}
          initialValues={{ is_active: true }}
          onValuesChange={(changedValues, allValues) => {
            if ('name' in changedValues && !editingCategory) {
              form.setFieldValue('slug', slugify(allValues.name ?? ''));
            }
          }}
          onFinish={(values) => saveMutation.mutate(values)}
        >
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="slug"
            label="Slug"
            rules={[{ required: true }]}
            help="Можно оставить автоматически сгенерированным"
          >
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}
