import React from 'react';
import { Typography } from 'antd';

export function PageTitle({ title, subtitle, extra }: { title: string; subtitle: string; extra?: React.ReactNode }) {
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
