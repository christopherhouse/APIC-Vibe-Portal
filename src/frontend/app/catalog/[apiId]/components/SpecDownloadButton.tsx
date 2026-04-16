'use client';

import Button from '@mui/material/Button';
import DownloadIcon from '@mui/icons-material/Download';

export interface SpecDownloadButtonProps {
  specContent: string | null;
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
  apiName,
  versionId,
  disabled,
}: SpecDownloadButtonProps) {
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
