'use client';

import { useState, useEffect, useCallback } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import Grid from '@mui/material/Grid';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import {
  fetchMcpCapabilities,
  invokeMcpTool,
  type McpCapabilities,
  type McpInvokeResult,
  type McpPrompt,
  type McpResource,
  type McpTool,
  type McpToolProperty,
} from '@/lib/mcp-inspector-api';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type CapabilitiesTab = 'tools' | 'prompts' | 'resources';

/** Render a JSON value into a formatted string for the result panel. */
function formatResultContent(result: McpInvokeResult): string {
  if (result.content.length === 0) return '(no content)';
  if (result.content.length === 1 && result.content[0]?.type === 'text') {
    return result.content[0].text ?? '(empty text)';
  }
  return JSON.stringify(result.content, null, 2);
}

// ---------------------------------------------------------------------------
// Schema-driven form
// ---------------------------------------------------------------------------

interface ToolFormProps {
  tool: McpTool;
  onInvoke: (args: Record<string, unknown>) => void;
  isInvoking: boolean;
}

function ToolForm({ tool, onInvoke, isInvoking }: ToolFormProps) {
  const properties = tool.inputSchema?.properties ?? {};
  const required = tool.inputSchema?.required ?? [];
  const propertyEntries = Object.entries(properties);

  const initialValues = Object.fromEntries(propertyEntries.map(([name]) => [name, '']));
  const [values, setValues] = useState<Record<string, string>>(initialValues);

  // Reset form when the selected tool changes
  useEffect(() => {
    const props = tool.inputSchema?.properties ?? {};
    setValues(Object.fromEntries(Object.keys(props).map((name) => [name, ''])));
  }, [tool.name, tool.inputSchema?.properties]);

  const handleSubmit = () => {
    const args: Record<string, unknown> = {};
    for (const [name, raw] of Object.entries(values)) {
      if (raw === '') continue;
      const prop: McpToolProperty | undefined = properties[name];
      if (prop?.type === 'number' || prop?.type === 'integer') {
        args[name] = Number(raw);
      } else if (prop?.type === 'boolean') {
        args[name] = raw === 'true';
      } else {
        args[name] = raw;
      }
    }
    onInvoke(args);
  };

  if (propertyEntries.length === 0) {
    return (
      <Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          This tool takes no input parameters.
        </Typography>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={isInvoking}
          data-testid="invoke-button"
        >
          {isInvoking ? 'Invoking…' : 'Invoke'}
        </Button>
      </Box>
    );
  }

  return (
    <Box
      component="form"
      onSubmit={(e) => {
        e.preventDefault();
        handleSubmit();
      }}
    >
      <Stack spacing={2} sx={{ mb: 2 }}>
        {propertyEntries.map(([name, prop]) => {
          const isRequired = required.includes(name);
          const label = `${name}${isRequired ? ' *' : ''}`;

          if (prop.enum && prop.enum.length > 0) {
            return (
              <TextField
                key={name}
                select
                label={label}
                value={values[name] ?? ''}
                onChange={(e) => setValues((prev) => ({ ...prev, [name]: e.target.value }))}
                helperText={prop.description}
                size="small"
                slotProps={{ htmlInput: { 'data-testid': `tool-input-${name}` } }}
              >
                <MenuItem value="">
                  <em>—</em>
                </MenuItem>
                {prop.enum.map((option) => (
                  <MenuItem key={option} value={option}>
                    {option}
                  </MenuItem>
                ))}
              </TextField>
            );
          }

          return (
            <TextField
              key={name}
              label={label}
              value={values[name] ?? ''}
              onChange={(e) => setValues((prev) => ({ ...prev, [name]: e.target.value }))}
              helperText={prop.description}
              type={prop.type === 'number' || prop.type === 'integer' ? 'number' : 'text'}
              size="small"
              slotProps={{ htmlInput: { 'data-testid': `tool-input-${name}` } }}
            />
          );
        })}
      </Stack>
      <Button type="submit" variant="contained" disabled={isInvoking} data-testid="invoke-button">
        {isInvoking ? 'Invoking…' : 'Invoke'}
      </Button>
    </Box>
  );
}

// ---------------------------------------------------------------------------
// Result panel
// ---------------------------------------------------------------------------

interface InvokeResultPanelProps {
  result: McpInvokeResult;
}

function InvokeResultPanel({ result }: InvokeResultPanelProps) {
  const formatted = formatResultContent(result);

  return (
    <Box data-testid="invoke-result">
      <Stack direction="row" spacing={1} sx={{ mb: 1, alignItems: 'center' }}>
        <Typography variant="subtitle2">Result</Typography>
        {result.isError ? (
          <Chip label="Error" color="error" size="small" />
        ) : (
          <Chip label="OK" color="success" size="small" />
        )}
        <Typography variant="caption" color="text.secondary">
          {result.durationMs.toFixed(0)} ms
        </Typography>
      </Stack>
      <Paper
        variant="outlined"
        sx={{
          p: 2,
          bgcolor: 'grey.50',
          maxHeight: 320,
          overflow: 'auto',
        }}
      >
        <Typography
          component="pre"
          sx={{ fontFamily: 'monospace', fontSize: '0.8rem', whiteSpace: 'pre-wrap', m: 0 }}
          data-testid="invoke-result-text"
        >
          {formatted}
        </Typography>
      </Paper>
    </Box>
  );
}

// ---------------------------------------------------------------------------
// Main tab component
// ---------------------------------------------------------------------------

export interface McpInspectorTabProps {
  apiId: string;
  serverUrl: string;
}

export default function McpInspectorTab({ apiId, serverUrl }: McpInspectorTabProps) {
  const [capabilities, setCapabilities] = useState<McpCapabilities | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [capTab, setCapTab] = useState<CapabilitiesTab>('tools');
  const [selectedTool, setSelectedTool] = useState<McpTool | null>(null);
  const [selectedPrompt, setSelectedPrompt] = useState<McpPrompt | null>(null);
  const [selectedResource, setSelectedResource] = useState<McpResource | null>(null);

  const [isInvoking, setIsInvoking] = useState(false);
  const [invokeError, setInvokeError] = useState<string | null>(null);
  const [invokeResult, setInvokeResult] = useState<McpInvokeResult | null>(null);

  const loadCapabilities = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setSelectedTool(null);
    setSelectedPrompt(null);
    setSelectedResource(null);
    setInvokeResult(null);
    setInvokeError(null);
    try {
      const caps = await fetchMcpCapabilities(apiId);
      setCapabilities(caps);
      if (caps.tools.length > 0) {
        setSelectedTool(caps.tools[0] ?? null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect to MCP server');
    } finally {
      setIsLoading(false);
    }
  }, [apiId]);

  useEffect(() => {
    void loadCapabilities();
  }, [loadCapabilities]);

  const handleInvoke = async (args: Record<string, unknown>) => {
    if (!selectedTool) return;
    setIsInvoking(true);
    setInvokeError(null);
    setInvokeResult(null);
    try {
      const result = await invokeMcpTool(apiId, selectedTool.name, args);
      setInvokeResult(result);
    } catch (err) {
      setInvokeError(err instanceof Error ? err.message : 'Tool invocation failed');
    } finally {
      setIsInvoking(false);
    }
  };

  // ------------------------------------------------------------------
  // Loading / error states
  // ------------------------------------------------------------------

  if (isLoading) {
    return (
      <Box
        sx={{ display: 'flex', justifyContent: 'center', py: 6 }}
        data-testid="inspector-loading"
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert
        severity="error"
        data-testid="inspector-error"
        action={
          <Button color="inherit" size="small" onClick={() => void loadCapabilities()}>
            Retry
          </Button>
        }
      >
        {error}
      </Alert>
    );
  }

  if (!capabilities) {
    return (
      <Alert severity="info" data-testid="inspector-empty">
        No capabilities available for this MCP server.
      </Alert>
    );
  }

  // ------------------------------------------------------------------
  // Helpers to render the right-hand detail pane
  // ------------------------------------------------------------------

  const renderDetailPane = () => {
    if (capTab === 'tools') {
      if (!selectedTool) {
        return (
          <Typography variant="body2" color="text.secondary">
            Select a tool from the list to inspect and invoke it.
          </Typography>
        );
      }

      return (
        <Stack spacing={2}>
          <Box>
            <Typography variant="h6" gutterBottom data-testid="selected-tool-name">
              {selectedTool.name}
            </Typography>
            {selectedTool.description && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {selectedTool.description}
              </Typography>
            )}
          </Box>

          <Divider />

          <Typography variant="subtitle2">Parameters</Typography>
          <ToolForm
            tool={selectedTool}
            onInvoke={(args) => void handleInvoke(args)}
            isInvoking={isInvoking}
          />

          {invokeError && (
            <Alert severity="error" data-testid="invoke-error">
              {invokeError}
            </Alert>
          )}

          {invokeResult && <InvokeResultPanel result={invokeResult} />}
        </Stack>
      );
    }

    if (capTab === 'prompts') {
      if (!selectedPrompt) {
        return (
          <Typography variant="body2" color="text.secondary">
            Select a prompt from the list to view its details.
          </Typography>
        );
      }

      return (
        <Stack spacing={1}>
          <Typography variant="h6" data-testid="selected-prompt-name">
            {selectedPrompt.name}
          </Typography>
          {selectedPrompt.description && (
            <Typography variant="body2" color="text.secondary">
              {selectedPrompt.description}
            </Typography>
          )}
          {selectedPrompt.arguments && selectedPrompt.arguments.length > 0 && (
            <>
              <Divider />
              <Typography variant="subtitle2">Arguments</Typography>
              <List dense>
                {selectedPrompt.arguments.map((arg) => (
                  <ListItemButton key={arg.name} disableRipple sx={{ pl: 0, cursor: 'default' }}>
                    <ListItemText
                      primary={`${arg.name}${arg.required ? ' *' : ''}`}
                      secondary={arg.description}
                    />
                  </ListItemButton>
                ))}
              </List>
            </>
          )}
        </Stack>
      );
    }

    if (capTab === 'resources') {
      if (!selectedResource) {
        return (
          <Typography variant="body2" color="text.secondary">
            Select a resource from the list to view its details.
          </Typography>
        );
      }

      return (
        <Stack spacing={1}>
          <Typography variant="h6" data-testid="selected-resource-name">
            {selectedResource.name}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
            {selectedResource.uri}
          </Typography>
          {selectedResource.description && (
            <Typography variant="body2">{selectedResource.description}</Typography>
          )}
          {selectedResource.mimeType && (
            <Chip label={selectedResource.mimeType} size="small" variant="outlined" />
          )}
        </Stack>
      );
    }

    return null;
  };

  // ------------------------------------------------------------------
  // Main render
  // ------------------------------------------------------------------

  return (
    <Box data-testid="mcp-inspector-tab" sx={{ py: 2 }}>
      {/* Connection strip */}
      <Stack direction="row" spacing={2} sx={{ mb: 2, alignItems: 'center' }}>
        <Chip label="Connected" color="success" size="small" data-testid="connection-status" />
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
          data-testid="server-url"
        >
          {serverUrl}
        </Typography>
        <Button
          size="small"
          variant="outlined"
          onClick={() => void loadCapabilities()}
          data-testid="reconnect-button"
        >
          Refresh
        </Button>
      </Stack>

      <Grid container spacing={2}>
        {/* Left rail: capability list */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
            {/* Capability type selector */}
            <Tabs
              value={capTab}
              onChange={(_e, v: CapabilitiesTab) => {
                setCapTab(v);
                setSelectedTool(null);
                setSelectedPrompt(null);
                setSelectedResource(null);
                setInvokeResult(null);
                setInvokeError(null);
              }}
              variant="fullWidth"
              data-testid="capability-tabs"
            >
              <Tab
                label={`Tools (${capabilities.tools.length})`}
                value="tools"
                data-testid="tools-tab"
              />
              <Tab
                label={`Prompts (${capabilities.prompts.length})`}
                value="prompts"
                data-testid="prompts-tab"
              />
              <Tab
                label={`Resources (${capabilities.resources.length})`}
                value="resources"
                data-testid="resources-tab"
              />
            </Tabs>

            {/* Item list */}
            <List dense data-testid="capability-list">
              {capTab === 'tools' &&
                (capabilities.tools.length === 0 ? (
                  <ListItemButton disableRipple sx={{ cursor: 'default' }}>
                    <ListItemText secondary="No tools available" />
                  </ListItemButton>
                ) : (
                  capabilities.tools.map((tool) => (
                    <ListItemButton
                      key={tool.name}
                      selected={selectedTool?.name === tool.name}
                      onClick={() => {
                        setSelectedTool(tool);
                        setInvokeResult(null);
                        setInvokeError(null);
                      }}
                      data-testid={`tool-item-${tool.name}`}
                    >
                      <ListItemText
                        primary={tool.name}
                        secondary={tool.description}
                        slotProps={{ secondary: { noWrap: true } }}
                      />
                    </ListItemButton>
                  ))
                ))}

              {capTab === 'prompts' &&
                (capabilities.prompts.length === 0 ? (
                  <ListItemButton disableRipple sx={{ cursor: 'default' }}>
                    <ListItemText secondary="No prompts available" />
                  </ListItemButton>
                ) : (
                  capabilities.prompts.map((prompt) => (
                    <ListItemButton
                      key={prompt.name}
                      selected={selectedPrompt?.name === prompt.name}
                      onClick={() => setSelectedPrompt(prompt)}
                      data-testid={`prompt-item-${prompt.name}`}
                    >
                      <ListItemText
                        primary={prompt.name}
                        secondary={prompt.description}
                        slotProps={{ secondary: { noWrap: true } }}
                      />
                    </ListItemButton>
                  ))
                ))}

              {capTab === 'resources' &&
                (capabilities.resources.length === 0 ? (
                  <ListItemButton disableRipple sx={{ cursor: 'default' }}>
                    <ListItemText secondary="No resources available" />
                  </ListItemButton>
                ) : (
                  capabilities.resources.map((resource) => (
                    <ListItemButton
                      key={resource.uri}
                      selected={selectedResource?.uri === resource.uri}
                      onClick={() => setSelectedResource(resource)}
                      data-testid={`resource-item-${resource.name}`}
                    >
                      <ListItemText
                        primary={resource.name}
                        secondary={resource.uri}
                        slotProps={{ secondary: { noWrap: true } }}
                      />
                    </ListItemButton>
                  ))
                ))}
            </List>
          </Paper>
        </Grid>

        {/* Right pane: detail / invoke */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Paper variant="outlined" sx={{ p: 2, minHeight: 200 }} data-testid="detail-pane">
            {renderDetailPane()}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
