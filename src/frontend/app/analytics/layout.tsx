import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Analytics - APIC Vibe Portal',
  description: 'Portal usage metrics, API popularity, and user engagement analytics',
};

export default function AnalyticsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
