import type { ReactNode } from 'react';
import { Typography } from 'antd';

type PageTitleProps = {
  title: string;
  subtitle: string;
  extra?: ReactNode;
};

export function PageTitle({ title, subtitle, extra }: PageTitleProps) {
  return (
    <div className="page-title">
      <div>
        <Typography.Title level={2}>{title}</Typography.Title>
        <Typography.Paragraph type="secondary">{subtitle}</Typography.Paragraph>
      </div>
      {extra}
    </div>
  );
}
