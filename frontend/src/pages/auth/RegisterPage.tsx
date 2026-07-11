import { useEffect } from 'react';
import { Button, Form, Input, Tabs, message } from 'antd';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { AuthLayout } from '../../components/layout/AuthLayout';
import { useAuth } from '../../hooks/useAuth';
import { AuthService, TokenResponse } from '../../api/generated';
import { extractErrorMessage } from '../../utils/api';

export function RegisterPage() {
  const [form] = Form.useForm<{
    identifier: string;
    identifier_type: 'email' | 'phone' | 'telegram';
    password: string;
  }>();
  const navigate = useNavigate();
  const { token, setToken } = useAuth();

  useEffect(() => {
    if (token) {
      navigate('/dashboard', { replace: true });
    }
  }, [navigate, token]);

  const registerMutation = useMutation({
    mutationFn: (values: { identifier: string; identifier_type: 'email' | 'phone' | 'telegram'; password: string }) =>
      AuthService.registerApiV1PublicAuthRegisterPost(values),
    onSuccess: (response: TokenResponse) => {
      setToken(response.access_token);
      void message.success('Регистрация выполнена');
      navigate('/dashboard');
    },
    onError: (error: unknown) => {
      void message.error(extractErrorMessage(error));
    },
  });

  return (
    <AuthLayout
      title="Регистрация"
      subtitle="JWT сохраняется в localStorage, а каждый запрос к generated client получает Bearer token"
      footer={
        <Button type="link" onClick={() => navigate('/login')}>
          Уже есть аккаунт? Войти
        </Button>
      }
    >
      <Form
        layout="vertical"
        form={form}
        initialValues={{ identifier_type: 'email' }}
        onFinish={(values) => registerMutation.mutate(values)}
      >
        <Form.Item
          label="Тип идентификатора"
          name="identifier_type"
          rules={[{ required: true, message: 'Выберите тип' }]}
        >
          <Tabs
            items={[
              { key: 'email', label: 'Email' },
              { key: 'phone', label: 'Phone' },
              { key: 'telegram', label: 'Telegram' },
            ]}
            onChange={(value) => form.setFieldValue('identifier_type', value)}
          />
        </Form.Item>
        <Form.Item label="Identifier" name="identifier" rules={[{ required: true, message: 'Укажите identifier' }]}>
          <Input />
        </Form.Item>
        <Form.Item
          label="Password"
          name="password"
          rules={[
            { required: true, message: 'Введите пароль' },
            { min: 8, message: 'Минимум 8 символов' },
          ]}
        >
          <Input.Password />
        </Form.Item>
        <Button type="primary" htmlType="submit" block loading={registerMutation.isPending}>
          Зарегистрироваться
        </Button>
      </Form>
    </AuthLayout>
  );
}
