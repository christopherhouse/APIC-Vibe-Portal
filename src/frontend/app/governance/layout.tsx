import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Governance Dashboard - APIC Vibe Portal',
  description: 'API governance metrics and compliance overview',
};

export default function GovernanceLayout({ children }: { children: React.ReactNode }) {
  return children;
}
