import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Search APIs - APIC Vibe Portal',
  description: 'Search and find APIs using keyword, semantic, or hybrid search',
};

export default function SearchLayout({ children }: { children: React.ReactNode }) {
  return children;
}
