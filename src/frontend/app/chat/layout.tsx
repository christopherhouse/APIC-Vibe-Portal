import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AI Assistant - APIC Vibe Portal',
  description: 'Chat with the AI assistant to discover and understand APIs',
};

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return children;
}
