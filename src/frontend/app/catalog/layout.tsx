import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'API Catalog - APIC Vibe Portal',
  description: 'Browse and discover APIs available in your organization',
};

export default function CatalogLayout({ children }: { children: React.ReactNode }) {
  return children;
}
