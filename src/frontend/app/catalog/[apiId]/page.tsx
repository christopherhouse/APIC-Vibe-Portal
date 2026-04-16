'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';

import { useApiDetail } from '@/hooks/use-api-detail';
import { useAuth } from '@/lib/auth/use-auth';
import ApiHeader from './components/ApiHeader';
import ApiTabs, { type ApiTabValue } from './components/ApiTabs';
import ApiMetadata from './components/ApiMetadata';
import ApiVersionList from './components/ApiVersionList';
import ApiSpecViewer from './components/ApiSpecViewer';
import ApiDeployments from './components/ApiDeployments';
import SpecDownloadButton from './components/SpecDownloadButton';

export default function ApiDetailPage() {
  const params = useParams<{ apiId: string }>();
  const apiId = params.apiId;
  const { isAuthenticated } = useAuth();

  const {
    api,
    versions,
    deployments,
    specContent,
    selectedVersionId,
    isLoading,
    isSpecLoading,
    error,
    specError,
    selectVersion,
    refetch,
  } = useApiDetail(apiId, { enabled: isAuthenticated });

  const [activeTab, setActiveTab] = useState<ApiTabValue>('overview');

  if (error && !api) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => void refetch()}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      {/* Header with breadcrumb, title, badges */}
      <Box sx={{ mb: 3 }}>
        <ApiHeader api={api} isLoading={isLoading} />
      </Box>

      {/* Tabs */}
      <ApiTabs value={activeTab} onChange={setActiveTab} />

      {/* Tab Content */}
      <Box>
        {activeTab === 'overview' && api && <ApiMetadata api={api} />}

        {activeTab === 'versions' && (
          <ApiVersionList
            versions={versions}
            selectedVersionId={selectedVersionId}
            onVersionChange={selectVersion}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'specification' && (
          <Box>
            <Stack direction="row" spacing={2} sx={{ mb: 2, alignItems: 'center' }}>
              <SpecDownloadButton
                specContent={specContent}
                apiName={api?.name ?? 'api'}
                versionId={selectedVersionId}
              />
            </Stack>
            <ApiSpecViewer
              specContent={specContent}
              isLoading={isSpecLoading}
              error={specError}
              onRetry={selectedVersionId ? () => selectVersion(selectedVersionId) : undefined}
            />
          </Box>
        )}

        {activeTab === 'deployments' && (
          <ApiDeployments deployments={deployments} isLoading={isLoading} />
        )}
      </Box>
    </Container>
  );
}
