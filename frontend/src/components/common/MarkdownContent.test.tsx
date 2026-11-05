import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarkdownContent } from './MarkdownContent';

describe('MarkdownContent', () => {
  it('renders markdown and preserves the caller class', () => {
    const { container } = render(<MarkdownContent className="message">{'**important**'}</MarkdownContent>);
    expect(screen.getByText('important').tagName).toBe('STRONG');
    expect(container.firstElementChild?.className).toBe('message');
  });

  it.each([null, undefined, ''])('handles empty message %s', (message) => {
    const { container } = render(<MarkdownContent>{message}</MarkdownContent>);
    expect(container.textContent).toBe('');
  });

  it('does not execute HTML or expose javascript links from chat messages', () => {
    const { container } = render(
      <MarkdownContent>{'<script>alert(1)</script>\n\n[click](javascript:alert%281%29)'}</MarkdownContent>
    );
    expect(container.querySelector('script')).toBeNull();
    const link = screen.getByText('click').closest('a');
    expect(link).not.toBeNull();
    expect(link?.getAttribute('href') ?? '').not.toMatch(/^javascript:/);
  });
});
