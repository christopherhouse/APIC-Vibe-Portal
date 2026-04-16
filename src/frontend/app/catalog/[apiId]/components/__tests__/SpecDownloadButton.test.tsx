import { render, screen, fireEvent } from '../../../../../__tests__/test-utils';
import SpecDownloadButton from '../SpecDownloadButton';

describe('SpecDownloadButton', () => {
  it('renders download button', () => {
    render(
      <SpecDownloadButton specContent='{"openapi":"3.0.0"}' apiName="test" versionId="v1" />,
    );
    expect(screen.getByTestId('spec-download-button')).toBeInTheDocument();
    expect(screen.getByText('Download Spec')).toBeInTheDocument();
  });

  it('is disabled when specContent is null', () => {
    render(<SpecDownloadButton specContent={null} apiName="test" versionId="v1" />);
    expect(screen.getByTestId('spec-download-button')).toBeDisabled();
  });

  it('is disabled when disabled prop is true', () => {
    render(
      <SpecDownloadButton specContent='{"test": true}' apiName="test" versionId="v1" disabled />,
    );
    expect(screen.getByTestId('spec-download-button')).toBeDisabled();
  });

  it('triggers download on click for JSON spec', () => {
    const originalCreateObjectURL = global.URL.createObjectURL;
    const originalRevokeObjectURL = global.URL.revokeObjectURL;
    const createObjectURL = jest.fn(() => 'blob:test');
    const revokeObjectURL = jest.fn();
    global.URL.createObjectURL = createObjectURL;
    global.URL.revokeObjectURL = revokeObjectURL;

    // Track link element creation via appendChild
    let capturedLink: HTMLAnchorElement | null = null;
    const originalAppendChild = document.body.appendChild.bind(document.body);
    const originalRemoveChild = document.body.removeChild.bind(document.body);

    try {
      jest.spyOn(document.body, 'appendChild').mockImplementation((node: Node) => {
        if (node instanceof HTMLAnchorElement) {
          capturedLink = node;
          jest.spyOn(node, 'click').mockImplementation(() => { /* no-op */ });
        }
        return originalAppendChild(node);
      });
      jest.spyOn(document.body, 'removeChild').mockImplementation((node: Node) => {
        if (node instanceof HTMLAnchorElement) {
          return node;
        }
        return originalRemoveChild(node);
      });

      render(
        <SpecDownloadButton specContent='{"openapi":"3.0.0"}' apiName="petstore" versionId="v1" />,
      );
      fireEvent.click(screen.getByTestId('spec-download-button'));
      expect(createObjectURL).toHaveBeenCalled();
      expect(capturedLink).not.toBeNull();
    } finally {
      if (capturedLink?.isConnected) {
        originalRemoveChild(capturedLink);
      }
      global.URL.createObjectURL = originalCreateObjectURL;
      global.URL.revokeObjectURL = originalRevokeObjectURL;
      jest.restoreAllMocks();
    }
  });
});
