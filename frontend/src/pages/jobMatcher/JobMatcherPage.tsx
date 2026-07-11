import { Card, Space, Typography } from 'antd';
import { PageTitle } from '../../components/common/PageTitle';

export function JobMatcherPage() {
  return (
    <Space direction="vertical" size="large" className="page-stack">
      <PageTitle title="Job Matcher" subtitle="Управление подписками и просмотр вакансий" />
      <Card>
        <Typography.Paragraph>
          Этот раздел пока в разработке. Здесь будет управление подписками на вакансии и просмотр подходящих
          предложений.
        </Typography.Paragraph>
      </Card>
    </Space>
  );
}
