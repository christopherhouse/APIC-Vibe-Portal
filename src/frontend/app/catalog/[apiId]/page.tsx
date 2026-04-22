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
import { ApiKind } from '@apic-vibe-portal/shared';
import ApiHeader from './components/ApiHeader';
import ApiTabs, { type ApiTabValue } from './components/ApiTabs';
import ApiMetadata from './components/ApiMetadata';
import ApiVersionList from './components/ApiVersionList';
import ApiSpecViewer from './components/ApiSpecViewer';
import ApiDeployments from './components/ApiDeployments';
import MetadataQualityTab from './components/MetadataQualityTab';
import SpecDownloadButton from './components/SpecDownloadButton';
import InstallInVsCodeButton from './components/InstallInVsCodeButton';
import CompareAddButton from '@/app/compare/components/CompareAddButton';

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

  const isMcp = api?.kind === ApiKind.MCP;
  const mcpServerUrl = isMcp ? (deployments[0]?.server.runtimeUri[0] ?? null) : null;

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      {/* Header with breadcrumb, title, badges */}
      <Box sx={{ mb: 3 }}>
        <ApiHeader api={api} isLoading={isLoading} />
        {api && (
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            <CompareAddButton apiId={api.name} variant="button" />
            {isMcp && <InstallInVsCodeButton serverUrl={mcpServerUrl} serverName={api.name} />}
          </Stack>
        )}
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

        {activeTab === 'metadata-quality' && apiId && <MetadataQualityTab apiId={apiId} />}
      </Box>
    </Container>
  );
}
