import { useState } from 'react';
import {
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Form,
  Popconfirm,
  Row,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import type { UploadFile } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import { FileRead, InternalService, MediaService } from '../../api/generated';
import { formatBytes, formatDate } from '../../utils/formatters';
import { extractErrorMessage } from '../../utils/api';

export function MediaPage() {
  const queryClient = useQueryClient();
  const [uploadForm] = Form.useForm<{ is_public: boolean }>();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedMedia, setSelectedMedia] = useState<FileRead | null>(null);

  const filesQuery = useQuery({
    queryKey: ['media', 'all'],
    queryFn: () => InternalService.listFilesInternalInternalMediaGet(undefined, 1, 100),
  });

  const uploadMutation = useMutation({
    mutationFn: async (values: { is_public: boolean }) => {
      if (!selectedFile) {
        throw new Error('Выберите файл');
      }

      return MediaService.uploadFileApiV1PublicMediaUploadPost({
        file: selectedFile,
        is_public: values.is_public,
      });
    },
    onSuccess: () => {
      setSelectedFile(null);
      uploadForm.resetFields();
      void message.success('Файл загружен');
      void queryClient.invalidateQueries({ queryKey: ['media'] });
    },
    onError: (error: unknown) => {
      void message.error(extractErrorMessage(error));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (fileId: string) => MediaService.deleteFileApiV1PublicMediaFileIdDelete(fileId),
    onSuccess: () => {
      void message.success('Файл удалён');
      void queryClient.invalidateQueries({ queryKey: ['media'] });
    },
    onError: (error: unknown) => {
      void message.error(extractErrorMessage(error));
    },
  });

  const columns = [
    { title: 'Filename', dataIndex: 'filename' },
    { title: 'Content type', dataIndex: 'content_type' },
    { title: 'Size', dataIndex: 'size_bytes', render: (value: number) => formatBytes(value) },
    {
      title: 'Public',
      dataIndex: 'is_public',
      render: (value: boolean) => <Tag color={value ? 'success' : 'default'}>{value ? 'yes' : 'no'}</Tag>,
    },
    { title: 'Created', dataIndex: 'created_at', render: (value: string) => formatDate(value) },
    {
      title: 'Actions',
      render: (_: unknown, record: FileRead) => (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setSelectedMedia(record);
              setDetailsOpen(true);
            }}
          >
            Просмотр
          </Button>
          <Button size="small" href={`/api/v1/public/media/${record.id}/download`} target="_blank">
            Скачать
          </Button>
          <Popconfirm title="Удалить файл?" onConfirm={() => deleteMutation.mutate(record.id)}>
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
      <PageTitle title="Media" subtitle="Список файлов, загрузка, просмотр и удаление" />
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={9}>
          <Card title="Загрузка файла">
            <Form
              layout="vertical"
              form={uploadForm}
              initialValues={{ is_public: false }}
              onFinish={(values) => uploadMutation.mutate(values)}
            >
              <Form.Item label="Файл" required>
                <Upload.Dragger
                  multiple={false}
                  beforeUpload={(file) => {
                    setSelectedFile(file as File);
                    return false;
                  }}
                  onRemove={() => {
                    setSelectedFile(null);
                    return true;
                  }}
                  fileList={
                    selectedFile
                      ? [
                          {
                            uid: selectedFile.name,
                            name: selectedFile.name,
                            status: 'done',
                          } as UploadFile,
                        ]
                      : []
                  }
                >
                  <p className="ant-upload-text">Перетащите файл сюда или нажмите для выбора</p>
                </Upload.Dragger>
              </Form.Item>
              <Form.Item name="is_public" label="Публичный доступ" valuePropName="checked">
                <Switch />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={uploadMutation.isPending}>
                Загрузить
              </Button>
            </Form>
          </Card>
        </Col>
        <Col xs={24} xl={15}>
          <Card title="Список файлов">
            <Table
              rowKey="id"
              loading={filesQuery.isLoading}
              columns={columns}
              dataSource={filesQuery.data?.items ?? []}
              pagination={false}
              scroll={{ x: 900 }}
            />
          </Card>
        </Col>
      </Row>
      <Drawer title="Метаданные файла" open={detailsOpen} onClose={() => setDetailsOpen(false)} width={560}>
        {selectedMedia ? (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="ID">
              <Typography.Text code>{selectedMedia.id}</Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Filename">{selectedMedia.filename}</Descriptions.Item>
            <Descriptions.Item label="Storage key">
              <Typography.Text code>{selectedMedia.storage_key}</Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Content type">{selectedMedia.content_type}</Descriptions.Item>
            <Descriptions.Item label="Size">{formatBytes(selectedMedia.size_bytes)}</Descriptions.Item>
            <Descriptions.Item label="Created">{formatDate(selectedMedia.created_at)}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Drawer>
    </Space>
  );
}
