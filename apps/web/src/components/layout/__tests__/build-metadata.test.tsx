import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import { BuildMetadata } from '../build-metadata';

// The global next-intl mock returns the raw key; make the strings readable so
// the assertions describe what the visitor sees.
jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => `t:${key}`,
}));

const mockFetch = global.fetch as unknown as jest.Mock;

/** The capability payload the backend answers with. */
function capabilitiesBody(build?: Record<string, string>) {
  return {
    auth: { jwt_enabled: false, oauth: { google: false, apple: false } },
    email: { enabled: false, provider: 'dummy' },
    llm: { demo_mode: true, default_provider: 'zai' },
    observability: { error_tracking: false },
    ...(build ? { build } : {}),
  };
}

function mockApi(build?: Record<string, string>) {
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/capabilities')) {
      return Promise.resolve(
        new Response(JSON.stringify(capabilitiesBody(build)), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );
    }
    return Promise.resolve(
      new Response(JSON.stringify({}), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });
}

describe('BuildMetadata', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  it('shows nothing to an ordinary visitor', async () => {
    mockApi();

    const { container } = render(<BuildMetadata />);

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the build to a privileged visitor', async () => {
    mockApi({
      sha: 'abc1234',
      built_at: '11.11.2026 02:00',
      deploy_run_id: '4242',
      commit_url: 'https://github.com/someone/some-repo/commit/abc1234',
      deploy_url: 'https://github.com/someone/some-repo/actions/runs/4242',
    });

    render(<BuildMetadata />);

    await waitFor(() => expect(screen.getByText('abc1234')).toBeInTheDocument());
    expect(screen.getByText('t:builtAt')).toBeInTheDocument();
    expect(screen.getByText('11.11.2026 02:00')).toBeInTheDocument();
    expect(screen.getByText('t:deployRun')).toBeInTheDocument();
    expect(screen.getByText('4242')).toBeInTheDocument();
    expect(screen.getByText('t:commit')).toBeInTheDocument();
  });

  it('links the commit and the deploy run', async () => {
    mockApi({
      sha: 'abc1234',
      built_at: '11.11.2026 02:00',
      deploy_run_id: '4242',
      commit_url: 'https://github.com/someone/some-repo/commit/abc1234',
      deploy_url: 'https://github.com/someone/some-repo/actions/runs/4242',
    });

    render(<BuildMetadata />);

    await waitFor(() => expect(screen.getByText('abc1234')).toBeInTheDocument());
    expect(screen.getByText('abc1234').closest('a')).toHaveAttribute(
      'href',
      'https://github.com/someone/some-repo/commit/abc1234'
    );
    expect(screen.getByText('4242').closest('a')).toHaveAttribute(
      'href',
      'https://github.com/someone/some-repo/actions/runs/4242'
    );
  });

  it('shows nothing when the deployment does not say which build it runs', async () => {
    mockApi({});

    const { container } = render(<BuildMetadata />);

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the value it has when the deployment carries no link', async () => {
    mockApi({ sha: 'abc1234' });

    render(<BuildMetadata />);

    await waitFor(() => expect(screen.getByText('abc1234')).toBeInTheDocument());
    // No link to break: the value is still worth showing.
    expect(screen.getByText('abc1234').closest('a')).toBeNull();
  });

  it('survives a deployment that cannot be asked', async () => {
    mockFetch.mockImplementation(() => Promise.reject(new Error('offline')));

    const { container } = render(<BuildMetadata />);

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});
