import { Button, Card, Popconfirm, Typography, message } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { PageTitle } from '../../components/common/PageTitle';
import { useAuth } from '../../hooks/useAuth';
import { AuthService } from '../../api/generated';
import { extractErrorMessage } from '../../utils/api';

export function DeleteAccountPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const mutation = useMutation({
    mutationFn: () => AuthService.deleteAccountApiV1PublicAuthMeDelete(),
    onSuccess: () => {
      logout();
      void message.success('Аккаунт удалён');
      navigate('/login');
    },
    onError: (error: unknown) => {
      void message.error(extractErrorMessage(error));
    },
  });

  return (
    <Card>
      <PageTitle title="Delete Account" subtitle="Удаление учётной записи с подтверждением на стороне интерфейса" />
      <Typography.Paragraph>Операция необратима. Она вызовет `DELETE /api/v1/public/auth/me`.</Typography.Paragraph>
      <Popconfirm
        title="Удалить аккаунт?"
        description="Профиль и связанные данные будут удалены."
        onConfirm={() => mutation.mutate()}
        okButtonProps={{ danger: true, loading: mutation.isPending }}
      >
        <Button danger icon={<DeleteOutlined />}>
          Удалить аккаунт
        </Button>
      </Popconfirm>
    </Card>
  );
}
