import { act, render, screen, waitFor, fireEvent } from '../../../../../__tests__/test-utils';
import McpInspectorTab from '../McpInspectorTab';
import * as mcpApi from '@/lib/mcp-inspector-api';

jest.mock('@/lib/mcp-inspector-api');

const mockFetchCapabilities = mcpApi.fetchMcpCapabilities as jest.MockedFunction<
  typeof mcpApi.fetchMcpCapabilities
>;
const mockInvokeTool = mcpApi.invokeMcpTool as jest.MockedFunction<typeof mcpApi.invokeMcpTool>;

const MOCK_CAPABILITIES: mcpApi.McpCapabilities = {
  serverUrl: 'https://mcp.example.com/sse',
  tools: [
    {
      name: 'get_weather',
      description: 'Get current weather',
      inputSchema: {
        type: 'object',
        properties: {
          location: { type: 'string', description: 'City name' },
          unit: { type: 'string', enum: ['celsius', 'fahrenheit'] },
        },
        required: ['location'],
      },
    },
    {
      name: 'no_params_tool',
      description: 'A tool with no parameters',
      inputSchema: { type: 'object', properties: {}, required: [] },
    },
  ],
  prompts: [
    {
      name: 'summarize',
      description: 'Summarize a document',
      arguments: [{ name: 'text', description: 'Document text', required: true }],
    },
  ],
  resources: [
    {
      uri: 'resource://catalog/products',
      name: 'Product Catalog',
      description: 'Full product list',
      mimeType: 'application/json',
    },
  ],
};

describe('McpInspectorTab', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading state while fetching capabilities', async () => {
    mockFetchCapabilities.mockReturnValue(new Promise(() => {}));

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    expect(screen.getByTestId('inspector-loading')).toBeInTheDocument();
  });

  it('shows error state when capabilities fetch fails', async () => {
    mockFetchCapabilities.mockRejectedValue(new Error('Connection refused'));

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('inspector-error')).toBeInTheDocument();
    });
    expect(screen.getByText('Connection refused')).toBeInTheDocument();
  });

  it('shows retry button in error state that reloads capabilities', async () => {
    mockFetchCapabilities
      .mockRejectedValueOnce(new Error('Timeout'))
      .mockResolvedValueOnce(MOCK_CAPABILITIES);

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('inspector-error')).toBeInTheDocument();
    });

    const retryBtn = screen.getByRole('button', { name: 'Retry' });
    await act(async () => {
      fireEvent.click(retryBtn);
    });

    await waitFor(() => {
      expect(screen.getByTestId('mcp-inspector-tab')).toBeInTheDocument();
    });
    expect(mockFetchCapabilities).toHaveBeenCalledTimes(2);
  });

  it('renders the inspector panel with connection status after loading', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('mcp-inspector-tab')).toBeInTheDocument();
    });
    expect(screen.getByTestId('connection-status')).toHaveTextContent('Connected');
    expect(screen.getByTestId('server-url')).toHaveTextContent('https://mcp.example.com/sse');
    expect(screen.getByTestId('reconnect-button')).toBeInTheDocument();
  });

  it('renders tool count in the tools tab label', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('tools-tab')).toBeInTheDocument();
    });
    expect(screen.getByTestId('tools-tab')).toHaveTextContent('Tools (2)');
    expect(screen.getByTestId('prompts-tab')).toHaveTextContent('Prompts (1)');
    expect(screen.getByTestId('resources-tab')).toHaveTextContent('Resources (1)');
  });

  it('lists all tools in the capability list', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('tool-item-get_weather')).toBeInTheDocument();
    });
    expect(screen.getByTestId('tool-item-no_params_tool')).toBeInTheDocument();
  });

  it('selects the first tool automatically and renders its form', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('selected-tool-name')).toHaveTextContent('get_weather');
    });
    expect(screen.getByTestId('invoke-button')).toBeInTheDocument();
  });

  it('renders text inputs for string tool parameters', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('tool-input-location')).toBeInTheDocument();
    });
  });

  it('renders a select for enum tool parameters', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      // The enum field 'unit' should render as a combobox/select
      expect(screen.getByTestId('tool-input-unit')).toBeInTheDocument();
    });
  });

  it('invokes the selected tool and shows the result', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);
    mockInvokeTool.mockResolvedValue({
      content: [{ type: 'text', text: 'Sunny, 22°C' }],
      isError: false,
      durationMs: 150,
    });

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('invoke-button')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('tool-input-location'), {
      target: { value: 'London' },
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('invoke-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('invoke-result')).toBeInTheDocument();
    });
    expect(screen.getByTestId('invoke-result-text')).toHaveTextContent('Sunny, 22°C');
    expect(mockInvokeTool).toHaveBeenCalledWith('my-mcp-server', 'get_weather', {
      location: 'London',
    });
  });

  it('shows an error chip when the invocation result has isError=true', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);
    mockInvokeTool.mockResolvedValue({
      content: [{ type: 'text', text: 'Tool failed: bad input' }],
      isError: true,
      durationMs: 42,
    });

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('invoke-button')).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('invoke-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('invoke-result')).toBeInTheDocument();
    });
    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('shows invoke error alert when tool invocation throws', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);
    mockInvokeTool.mockRejectedValue(new Error('Network failure'));

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('invoke-button')).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('invoke-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('invoke-error')).toBeInTheDocument();
    });
    expect(screen.getByText('Network failure')).toBeInTheDocument();
  });

  it('switches to prompts tab and shows prompt list', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('prompts-tab')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('prompts-tab'));

    await waitFor(() => {
      expect(screen.getByTestId('prompt-item-summarize')).toBeInTheDocument();
    });
  });

  it('switches to resources tab and shows resource list', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('resources-tab')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('resources-tab'));

    await waitFor(() => {
      expect(screen.getByTestId('resource-item-Product Catalog')).toBeInTheDocument();
    });
  });

  it('refresh button reloads capabilities', async () => {
    mockFetchCapabilities.mockResolvedValue(MOCK_CAPABILITIES);

    render(<McpInspectorTab apiId="my-mcp-server" serverUrl="https://mcp.example.com/sse" />);

    await waitFor(() => {
      expect(screen.getByTestId('reconnect-button')).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('reconnect-button'));
    });

    expect(mockFetchCapabilities).toHaveBeenCalledTimes(2);
  });
});
