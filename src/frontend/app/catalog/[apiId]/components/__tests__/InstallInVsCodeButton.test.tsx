import { render, screen, fireEvent } from '../../../../../__tests__/test-utils';
import InstallInVsCodeButton from '../InstallInVsCodeButton';

const SERVER_URL = 'https://mcp.example.com/sse';
const SERVER_NAME = 'my-mcp-server';

describe('InstallInVsCodeButton', () => {
  it('renders the install button', () => {
    render(<InstallInVsCodeButton serverUrl={SERVER_URL} serverName={SERVER_NAME} />);
    expect(screen.getByTestId('install-vscode-button')).toBeInTheDocument();
    expect(screen.getByText('Install in VS Code')).toBeInTheDocument();
  });

  it('renders the VS Code logo image', () => {
    render(<InstallInVsCodeButton serverUrl={SERVER_URL} serverName={SERVER_NAME} />);
    const img = screen.getByRole('img', { name: 'Visual Studio Code' });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', '/vscode-logo.svg');
  });

  it('is enabled when serverUrl is provided', () => {
    render(<InstallInVsCodeButton serverUrl={SERVER_URL} serverName={SERVER_NAME} />);
    expect(screen.getByTestId('install-vscode-button')).not.toBeDisabled();
  });

  it('is disabled when serverUrl is null', () => {
    render(<InstallInVsCodeButton serverUrl={null} serverName={SERVER_NAME} />);
    expect(screen.getByTestId('install-vscode-button')).toBeDisabled();
  });

  it('navigates to the correct vscode:// deep-link on click', () => {
    const openSpy = jest.spyOn(window, 'open').mockImplementation(() => null);

    render(<InstallInVsCodeButton serverUrl={SERVER_URL} serverName={SERVER_NAME} />);
    fireEvent.click(screen.getByTestId('install-vscode-button'));

    expect(openSpy).toHaveBeenCalledTimes(1);
    const calledUrl = openSpy.mock.calls[0]?.[0] as string;
    expect(calledUrl).toMatch(/^vscode:\/\/ms-vscode\.azure-api-center\/installMcpServer/);
    expect(calledUrl).toContain(`url=${encodeURIComponent(SERVER_URL)}`);
    expect(calledUrl).toContain(`name=${encodeURIComponent(SERVER_NAME)}`);
    expect(openSpy.mock.calls[0]?.[1]).toBe('_self');

    openSpy.mockRestore();
  });

  it('does not navigate when serverUrl is null and button is clicked', () => {
    const openSpy = jest.spyOn(window, 'open').mockImplementation(() => null);

    render(<InstallInVsCodeButton serverUrl={null} serverName={SERVER_NAME} />);
    // Button is disabled — handler must not fire
    fireEvent.click(screen.getByTestId('install-vscode-button'));
    expect(openSpy).not.toHaveBeenCalled();

    openSpy.mockRestore();
  });
});
