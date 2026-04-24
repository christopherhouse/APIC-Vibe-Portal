'use client';

import Button from '@mui/material/Button';
import DownloadIcon from '@mui/icons-material/Download';
import { useAnalytics } from '@/lib/analytics/use-analytics';

export interface SpecDownloadButtonProps {
  specContent: string | null;
  apiId: string;
  apiName: string;
  versionId: string | null;
  disabled?: boolean;
}

/**
 * Download button for the API specification.
 * Creates a Blob from the spec content and triggers a browser download.
 */
export default function SpecDownloadButton({
  specContent,
  apiId,
  apiName,
  versionId,
  disabled,
}: SpecDownloadButtonProps) {
  const { track } = useAnalytics();

  const handleDownload = () => {
    if (!specContent) return;

    // Detect JSON vs YAML
    let isJson = false;
    try {
      JSON.parse(specContent);
      isJson = true;
    } catch {
      // Not JSON, treat as YAML
    }

    const extension = isJson ? 'json' : 'yaml';
    const mimeType = isJson ? 'application/json' : 'text/yaml';
    const filename = `${apiName}-${versionId ?? 'spec'}.${extension}`;

    const blob = new Blob([specContent], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    track.specDownload({ apiId, format: extension as 'json' | 'yaml' });
  };

  return (
    <Button
      variant="outlined"
      size="small"
      startIcon={<DownloadIcon />}
      onClick={handleDownload}
      disabled={disabled || !specContent}
      data-testid="spec-download-button"
    >
      Download Spec
    </Button>
  );
}
