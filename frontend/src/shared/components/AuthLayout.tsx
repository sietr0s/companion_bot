import type { ReactNode } from 'react';
import { Card, Typography } from 'antd';

type AuthLayoutProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
};

export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className="auth-page">
      <Card className="auth-card">
        <Typography.Title level={2}>{title}</Typography.Title>
        <Typography.Paragraph type="secondary">{subtitle}</Typography.Paragraph>
        {children}
        <div className="auth-footer">{footer}</div>
      </Card>
    </div>
  );
}
