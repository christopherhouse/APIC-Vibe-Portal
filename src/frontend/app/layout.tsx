import type { Metadata } from 'next';
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { Suspense } from 'react';
import theme from '@/lib/theme';
import AuthProvider from '@/lib/auth/auth-provider';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import Footer from '@/components/layout/Footer';
import { ChatProvider } from '@/lib/chat-context';
import { SidebarProvider } from '@/lib/sidebar-context';
import ChatSidePanel from '@/app/chat/components/ChatSidePanel';
import TelemetryProvider from '@/components/TelemetryProvider';
import AnalyticsProvider from '@/lib/analytics/analytics-provider';
import './globals.css';

export const metadata: Metadata = {
  title: 'APIC Vibe Portal',
  description: 'AI-powered API portal for discovering, understanding, and using APIs',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppRouterCacheProvider>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            <Suspense fallback={null}>
              <TelemetryProvider />
            </Suspense>
            <AuthProvider>
              <AnalyticsProvider>
                <ChatProvider>
                  <SidebarProvider>
                    <Box sx={{ display: 'flex', minHeight: '100vh', flexDirection: 'column' }}>
                      <Header />
                      <Box sx={{ display: 'flex', flex: 1 }}>
                        <Sidebar />
                        <Box
                          component="main"
                          sx={{
                            flexGrow: 1,
                            p: 3,
                            mt: 'var(--header-height)',
                            minHeight: `calc(100vh - var(--header-height) - var(--footer-height))`,
                          }}
                        >
                          {children}
                        </Box>
                      </Box>
                      <Footer />
                      <ChatSidePanel />
                    </Box>
                  </SidebarProvider>
                </ChatProvider>
              </AnalyticsProvider>
            </AuthProvider>
          </ThemeProvider>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
