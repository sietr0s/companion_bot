import { useEffect } from 'react';
import { Button, Form, Input, message } from 'antd';
import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { AuthLayout } from '../../components/layout/AuthLayout';
import { useAuth } from '../../hooks/useAuth';
import { AuthService, TokenResponse } from '../../api/generated';
import { extractErrorMessage } from '../../utils/api';

export function LoginPage() {
  const [form] = Form.useForm<{ identifier: string; password: string }>();
  const navigate = useNavigate();
  const { token, setToken } = useAuth();

  useEffect(() => {
    if (token) {
      navigate('/dashboard', { replace: true });
    }
  }, [navigate, token]);

  const loginMutation = useMutation({
    mutationFn: (values: { identifier: string; password: string }) => AuthService.loginApiV1PublicAuthLoginPost(values),
    onSuccess: (response: TokenResponse) => {
      setToken(response.access_token);
      void message.success('Вход выполнен');
      navigate('/dashboard');
    },
    onError: (error: unknown) => {
      void message.error(extractErrorMessage(error));
    },
  });

  return (
    <AuthLayout
      title="Вход"
      subtitle="Админ-панель работает поверх автогенерированного клиента из openapi.json"
      footer={
        <Button type="link" onClick={() => navigate('/register')}>
          Нет аккаунта? Зарегистрироваться
        </Button>
      }
    >
      <Form layout="vertical" form={form} onFinish={(values) => loginMutation.mutate(values)}>
        <Form.Item
          label="Identifier"
          name="identifier"
          rules={[{ required: true, message: 'Укажите email, телефон или telegram' }]}
        >
          <Input placeholder="user@example.com / +7900... / @username" />
        </Form.Item>
        <Form.Item label="Password" name="password" rules={[{ required: true, message: 'Введите пароль' }]}>
          <Input.Password prefix={<LockOutlined />} />
        </Form.Item>
        <Button type="primary" htmlType="submit" block loading={loginMutation.isPending} icon={<UserOutlined />}>
          Войти
        </Button>
      </Form>
    </AuthLayout>
  );
}
