'use client';

import Button from '@mui/material/Button';
import Tooltip from '@mui/material/Tooltip';
import Box from '@mui/material/Box';

export interface InstallInVsCodeButtonProps {
  /** The MCP server URL to install. Button is disabled when null. */
  serverUrl: string | null;
  /** The display name for the MCP server. */
  serverName: string;
}

/**
 * Builds the VS Code deep-link URL that triggers the Azure API Center
 * extension to install the given MCP server.
 *
 * URL scheme: vscode://ms-vscode.azure-api-center/installMcpServer
 *   ?name=<encoded-name>&url=<encoded-server-url>
 */
function buildVsCodeInstallUrl(serverName: string, serverUrl: string): string {
  const params = new URLSearchParams({
    name: serverName,
    url: serverUrl,
  });
  return `vscode://ms-vscode.azure-api-center/installMcpServer?${params.toString()}`;
}

const VsCodeIcon = () => (
  <Box
    component="img"
    src="/vscode-logo.svg"
    alt="Visual Studio Code"
    sx={{ width: 18, height: 18, display: 'block' }}
  />
);

/**
 * Button that opens VS Code and installs the MCP server via the VS Code
 * protocol handler. Shown only for APIs of kind "mcp".
 */
export default function InstallInVsCodeButton({
  serverUrl,
  serverName,
}: InstallInVsCodeButtonProps) {
  const handleInstall = () => {
    if (!serverUrl) return;
    window.open(buildVsCodeInstallUrl(serverName, serverUrl), '_self');
  };

  return (
    <Tooltip
      title={
        serverUrl
          ? 'Open VS Code and install this MCP server'
          : 'No server URL available for installation'
      }
    >
      {/* Tooltip requires a single child that can hold a ref; wrap disabled button in span */}
      <span>
        <Button
          variant="contained"
          size="small"
          startIcon={<VsCodeIcon />}
          onClick={handleInstall}
          disabled={!serverUrl}
          data-testid="install-vscode-button"
          sx={{ textTransform: 'none' }}
        >
          Install in VS Code
        </Button>
      </span>
    </Tooltip>
  );
}
