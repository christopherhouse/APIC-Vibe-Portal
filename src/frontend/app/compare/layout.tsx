import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Compare APIs - APIC Vibe Portal',
  description: 'Compare API specifications, capabilities, and metadata side-by-side',
};

export default function CompareLayout({ children }: { children: React.ReactNode }) {
  return children;
}
