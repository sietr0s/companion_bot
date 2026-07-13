import { useEffect } from 'react';
import { Button, Card, Form, Input, Space, Switch, message } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { PageTitle } from '../../components/common/PageTitle';
import { ApiError, TelegramClientsService } from '../../api/generated';
import { extractErrorMessage } from '../../utils/api';

export function TelegramSettingsPage() {
  const { accountId } = useParams<{ accountId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [settingsForm] = Form.useForm<{
    read_groups: boolean;
    read_personal: boolean;
    read_channels: boolean;
    whitelist_chat_ids: string;
  }>();

  const accountQuery = useQuery({
    queryKey: ['telegram', 'account', accountId],
    enabled: Boolean(accountId),
    queryFn: () => TelegramClientsService.getAccountApiV1PublicTelegramAccountIdGet(accountId!),
  });

  const settingsQuery = useQuery({
    queryKey: ['telegram', 'settings', accountId],
    enabled: Boolean(accountId),
    queryFn: () => TelegramClientsService.getSettingsApiV1PublicTelegramAccountIdSettingsGet(accountId!),
  });

  useEffect(() => {
    if (settingsQuery.data) {
      settingsForm.setFieldsValue({
        read_groups: settingsQuery.data.read_groups,
        read_personal: settingsQuery.data.read_personal,
        read_channels: settingsQuery.data.read_channels,
        whitelist_chat_ids: settingsQuery.data.whitelist_chat_ids.join(', '),
      });
    } else if (settingsQuery.error instanceof ApiError && settingsQuery.error.status === 404) {
      settingsForm.setFieldsValue({
        read_groups: true,
        read_personal: true,
        read_channels: false,
        whitelist_chat_ids: '',
      });
    }
  }, [settingsForm, settingsQuery.data, settingsQuery.error]);

  const settingsMutation = useMutation({
    mutationFn: async (values: {
      read_groups: boolean;
      read_personal: boolean;
      read_channels: boolean;
      whitelist_chat_ids: string;
    }) => {
      const whitelistChatIds = values.whitelist_chat_ids
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);

      if (settingsQuery.data) {
        return TelegramClientsService.updateSettingsApiV1PublicTelegramAccountIdSettingsPut(accountId!, {
          read_groups: values.read_groups,
          read_personal: values.read_personal,
          read_channels: values.read_channels,
        });
      }

      return TelegramClientsService.createSettingsApiV1PublicTelegramAccountIdSettingsPost(accountId!, {
        read_groups: values.read_groups,
        read_personal: values.read_personal,
        read_channels: values.read_channels,
        whitelist_chat_ids: whitelistChatIds,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['telegram', 'settings', accountId] });
      void message.success('Настройки сохранены');
    },
    onError: (error: unknown) => void message.error(extractErrorMessage(error)),
  });

  const phone = accountQuery.data?.phone ?? `Аккаунт ${accountId}`;

  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle
        title={`Настройки — ${phone}`}
        subtitle="Настройки чтения Telegram-аккаунта"
        extra={
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/telegram/${accountId}/chats`)}>
            Назад к чатам
          </Button>
        }
      />
      <Card title="Настройки чтения">
        <Form
          layout="vertical"
          form={settingsForm}
          onFinish={(values) => settingsMutation.mutate(values)}
          style={{ maxWidth: 480 }}
        >
          <Form.Item name="read_groups" label="Read groups" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="read_personal" label="Read personal" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="read_channels" label="Read channels" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="whitelist_chat_ids" label="Whitelist chat ids">
            <Input.TextArea rows={4} placeholder="1, 2, -100123..." />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={settingsMutation.isPending}>
            Сохранить настройки
          </Button>
        </Form>
      </Card>
    </Space>
  );
}