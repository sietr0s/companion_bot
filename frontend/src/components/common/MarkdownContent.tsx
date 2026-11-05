import type { ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';

type MarkdownContentProps = {
  children: string | null | undefined;
  className?: string;
};

export function MarkdownContent({ children, className }: MarkdownContentProps): ReactNode {
  return (
    <div className={className}>
      <ReactMarkdown>{children ?? ''}</ReactMarkdown>
    </div>
  );
}
