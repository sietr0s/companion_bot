import { Button, Card, Form, Input, message } from 'antd';
import { useMutation } from '@tanstack/react-query';
import { PageTitle } from '../../components/common/PageTitle';
import { AuthService } from '../../api/generated';
import { extractErrorMessage } from '../../utils/api';

export function ChangePasswordPage() {
  const [form] = Form.useForm<{ current_password: string; new_password: string }>();
  const mutation = useMutation({
    mutationFn: (values: { current_password: string; new_password: string }) =>
      AuthService.changePasswordApiV1PublicAuthMePasswordPatch(values),
    onSuccess: () => {
      form.resetFields();
      void message.success('Пароль обновлён');
    },
    onError: (error: unknown) => {
      void message.error(extractErrorMessage(error));
    },
  });

  return (
    <Card>
      <PageTitle title="Change Password" subtitle="Форма работает на `PATCH /api/v1/public/auth/me/password`" />
      <Form layout="vertical" form={form} onFinish={(values) => mutation.mutate(values)} className="narrow-form">
        <Form.Item name="current_password" label="Current password" rules={[{ required: true }]}>
          <Input.Password />
        </Form.Item>
        <Form.Item
          name="new_password"
          label="New password"
          rules={[{ required: true }, { min: 8, message: 'Минимум 8 символов' }]}
        >
          <Input.Password />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={mutation.isPending}>
          Обновить пароль
        </Button>
      </Form>
    </Card>
  );
}
