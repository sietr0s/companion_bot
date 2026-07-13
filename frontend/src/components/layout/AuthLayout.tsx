import React from 'react';
import { Card, Typography } from 'antd';

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="auth-page">
      <Card className="auth-card">
        <Typography.Title level={2}>{title}</Typography.Title>
        <Typography.Paragraph type="secondary">{subtitle}</Typography.Paragraph>
        {children}
        {footer ? <div className="auth-footer">{footer}</div> : null}
      </Card>
    </div>
  );
}
