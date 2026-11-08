import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import ChatPage from '../page';
import { streamChatMessage, ApiError } from '@/lib/api';

// Mock the API module
jest.mock('@/lib/api', () => {
  class MockApiError extends Error {
    constructor(
      message: string,
      public status: number,
      public request_id?: string
    ) {
      super(message);
      this.name = 'ApiError';
    }
  }
  return {
    streamChatMessage: jest.fn(),
    ApiError: MockApiError,
  };
});

// The global next-intl mock returns the raw translation key. The page renders
// user-visible English, so the mock resolves the real `en` messages (including
// `{placeholder}` interpolation such as the error apology and the request id).
jest.mock('next-intl', () => {
  const messages = jest.requireActual<Record<string, unknown>>('../../../../../messages/en.json');
  const resolve = (path: string): unknown =>
    path.split('.').reduce<unknown>(
      (acc, part) =>
        acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[part] : undefined,
      messages
    );
  const interpolate = (template: string, params?: Record<string, unknown>) =>
    params
      ? template.replace(/\{(\w+)\}/g, (match, name) =>
          name in params ? String(params[name]) : match
        )
      : template;
  return {
    useTranslations:
      (namespace?: string) =>
      (key: string, params?: Record<string, unknown>) => {
        const value = resolve(namespace ? `${namespace}.${key}` : key);
        return typeof value === 'string' ? interpolate(value, params) : key;
      },
    useLocale: () => 'en',
    useMessages: () => messages,
    NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
  };
});

const mockStream = streamChatMessage as jest.Mock;
beforeEach(() => {
  jest.clearAllMocks();
});

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = jest.fn();

describe('ChatPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders chat interface', () => {
    render(<ChatPage />);
    expect(
      screen.getByPlaceholderText('Type your question here to get started...')
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument();
  });

  it('displays initial greeting', () => {
    render(<ChatPage />);
    expect(screen.getByRole('heading', { name: 'AI Assistant' })).toBeInTheDocument();
    expect(
      screen.getByText('Ask questions about properties, neighborhoods, and market trends.')
    ).toBeInTheDocument();
  });

  it('handles message submission', async () => {
    mockStream.mockImplementation(async (_req, onChunk, onStart, onMeta) => {
      onStart?.({ requestId: 'req-1' });
      await new Promise((resolve) => setTimeout(resolve, 0));
      onChunk('This is a real API response');
      await new Promise((resolve) => setTimeout(resolve, 0));
      onMeta?.({});
      return Promise.resolve();
    });

    render(<ChatPage />);

    const input = screen.getByPlaceholderText('Type your question here to get started...');
    const sendButton = screen.getByRole('button', { name: /send message/i });

    await act(async () => {
      fireEvent.change(input, { target: { value: 'Find me a house' } });
      fireEvent.click(sendButton);
    });

    // Wait for user message to appear (state update may be batched)
    await waitFor(() => {
      expect(screen.getByText('Find me a house')).toBeInTheDocument();
    });

    // Input should be cleared
    expect(input).toHaveValue('');

    // Wait for bot response
    await waitFor(() => {
      expect(screen.getByText('This is a real API response')).toBeInTheDocument();
    });
  });

  it('handles loading state', async () => {
    mockStream.mockImplementation(
      () =>
        new Promise<void>((resolve) =>
          setTimeout(() => {
            resolve();
          }, 100)
        )
    );

    render(<ChatPage />);

    const input = screen.getByPlaceholderText('Type your question here to get started...');
    const sendButton = screen.getByRole('button', { name: /send message/i });

    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(sendButton);

    expect(screen.getByLabelText('Thinking...')).toBeInTheDocument();
    expect(sendButton).toBeDisabled();

    await waitFor(() => {
      expect(screen.queryByLabelText('Thinking...')).not.toBeInTheDocument();
    });
  });

  it('handles error state', async () => {
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    mockStream.mockRejectedValueOnce(new ApiError('Failed to start stream', 500, 'req-xyz'));

    render(<ChatPage />);

    const input = screen.getByPlaceholderText('Type your question here to get started...');
    const sendButton = screen.getByRole('button', { name: /send message/i });

    fireEvent.change(input, { target: { value: 'Error' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(
        screen.getByText(
          'I apologize, but I encountered an error: Failed to start stream. Please try again.'
        )
      ).toBeInTheDocument();
    });
    expect(screen.getByText('request_id=req-xyz')).toBeInTheDocument();
    expect(warnSpy).not.toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it('shows retry button and retries stream', async () => {
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    mockStream
      .mockRejectedValueOnce(new ApiError('Failed to start stream', 500, 'req-123'))
      .mockImplementationOnce(async (_req, onChunk, _onStart, onMeta) => {
        await new Promise((resolve) => setTimeout(resolve, 0));
        onChunk('Recovered response');
        await new Promise((resolve) => setTimeout(resolve, 0));
        onMeta?.({});
        return Promise.resolve();
      });

    render(<ChatPage />);

    const input = screen.getByPlaceholderText('Type your question here to get started...');
    const sendButton = screen.getByRole('button', { name: /send message/i });

    fireEvent.change(input, { target: { value: 'Retry test' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });
    expect(screen.getByText('request_id=req-123')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /retry/i }));

    await waitFor(() => {
      expect(screen.getByText(/Recovered response/)).toBeInTheDocument();
    });
    expect(warnSpy).not.toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it('renders sources when provided by stream metadata', async () => {
    mockStream.mockImplementation(async (_req, onChunk, _onStart, onMeta) => {
      await new Promise((resolve) => setTimeout(resolve, 0));
      onChunk('Answer');
      await new Promise((resolve) => setTimeout(resolve, 0));
      onMeta?.({
        sessionId: 'sid-1',
        sources: [{ content: 'Doc', metadata: { id: '1' } }],
        sourcesTruncated: true,
      });
      return Promise.resolve();
    });

    render(<ChatPage />);

    const input = screen.getByPlaceholderText('Type your question here to get started...');
    const sendButton = screen.getByRole('button', { name: /send message/i });

    fireEvent.change(input, { target: { value: 'Show sources' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText('Answer')).toBeInTheDocument();
    });

    expect(screen.getByText('Citations (1)')).toBeInTheDocument();
    expect(screen.getByText('((truncated))')).toBeInTheDocument();
    // The citation itself is listed; the snippet stays collapsed until expanded.
    expect(screen.getByText('Source 1')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /show snippet/i }));
    expect(screen.getByText('Doc')).toBeInTheDocument();
  });

  it('does not submit empty message', async () => {
    render(<ChatPage />);

    const sendButton = screen.getByRole('button', { name: /send message/i });

    fireEvent.click(sendButton);

    expect(mockStream).not.toHaveBeenCalled();
  });
});
