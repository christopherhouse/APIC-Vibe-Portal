/**
 * Lightweight mock for react-markdown used in Jest tests.
 *
 * Renders the markdown content as plain text inside a <div> so tests can
 * assert on the text content without needing the full ESM package.
 */
import React from 'react';

interface ReactMarkdownProps {
  children?: string;
}

export default function ReactMarkdown({ children }: ReactMarkdownProps) {
  return <div data-testid="markdown-content">{children}</div>;
}
