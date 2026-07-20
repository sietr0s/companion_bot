import { useEffect } from 'react';
import { Button, Card, Form, Space, Switch, message } from 'antd';
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
    use_whitelist: boolean;
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
        use_whitelist: settingsQuery.data.use_whitelist,
      });
    } else if (settingsQuery.error instanceof ApiError && settingsQuery.error.status === 404) {
      settingsForm.setFieldsValue({
        use_whitelist: true,
      });
    }
  }, [settingsForm, settingsQuery.data, settingsQuery.error]);

  const settingsMutation = useMutation({
    mutationFn: async (values: {
      use_whitelist: boolean;
    }) => {
      if (settingsQuery.data) {
        return TelegramClientsService.updateSettingsApiV1PublicTelegramAccountIdSettingsPut(accountId!, {
          use_whitelist: values.use_whitelist,
        });
      }

      return TelegramClientsService.createSettingsApiV1PublicTelegramAccountIdSettingsPost(accountId!, {
        use_whitelist: values.use_whitelist,
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
          <Form.Item name="use_whitelist" label="Использовать whitelist" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={settingsMutation.isPending}>
            Сохранить настройки
          </Button>
        </Form>
      </Card>
    </Space>
  );
}
