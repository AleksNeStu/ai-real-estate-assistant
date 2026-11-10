import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import {
  ModelCatalogue,
  formatContextWindow,
  formatPricePer1m,
  isMissingKeyMessage,
  probeTone,
} from '../model-catalogue';
import { testModelRuntime } from '@/lib/api';
import type { ModelProviderCatalog } from '@/lib/types';

jest.mock('@/lib/api', () => ({
  testModelRuntime: jest.fn(),
}));

const catalog: ModelProviderCatalog[] = [
  {
    name: 'openai',
    display_name: 'OpenAI',
    is_local: false,
    requires_api_key: true,
    models: [
      {
        id: 'gpt-4o',
        display_name: 'GPT-4o',
        provider_name: 'OpenAI',
        context_window: 128000,
        pricing: { input_price_per_1m: 2.5, output_price_per_1m: 10, currency: 'USD' },
        capabilities: [],
        description: null,
        recommended_for: [],
      },
      {
        id: 'gpt-4o-mini',
        display_name: 'GPT-4o mini',
        provider_name: 'OpenAI',
        context_window: 1000000,
        pricing: null,
        capabilities: [],
        description: null,
        recommended_for: [],
      },
    ],
    runtime_available: null,
    available_models: null,
    runtime_error: null,
  },
];

describe('the context window', () => {
  it('reads in the shape a reader scans', () => {
    expect(formatContextWindow(128000)).toBe('128k');
    expect(formatContextWindow(1000000)).toBe('1M');
    expect(formatContextWindow(8192)).toBe('8.2k');
  });

  it('says nothing when the catalogue carries no size', () => {
    expect(formatContextWindow(undefined)).toBe('—');
    expect(formatContextWindow(0)).toBe('—');
  });
});

describe('the price of a million tokens', () => {
  it('carries the currency the catalogue gives', () => {
    expect(formatPricePer1m(2.5, 'USD')).toBe('USD 2.50');
  });

  it('says nothing when the catalogue carries no price', () => {
    expect(formatPricePer1m(undefined, 'USD')).toBe('—');
  });
});

describe('the probe', () => {
  it('tells a missing key from a failure', () => {
    expect(isMissingKeyMessage('API key not provided')).toBe(true);
    expect(isMissingKeyMessage('Connection failed: timeout')).toBe(false);
    expect(isMissingKeyMessage(undefined)).toBe(false);
  });

  it('keeps the status meaning in its tone', () => {
    expect(probeTone({ state: 'ok' })).toBe('success');
    expect(probeTone({ state: 'missing-key' })).toBe('warning');
    expect(probeTone({ state: 'failed' })).toBe('destructive');
    expect(probeTone({ state: 'idle' })).toBe('neutral');
  });
});

describe('the catalogue', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders every model with its context and its prices', () => {
    render(<ModelCatalogue catalog={catalog} />);

    expect(screen.getByText('gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('128k')).toBeInTheDocument();
    expect(screen.getByText('1M')).toBeInTheDocument();
    expect(screen.getByText('USD 2.50')).toBeInTheDocument();
    expect(screen.getByText('USD 10.00')).toBeInTheDocument();
    // The model the catalogue does not price carries no made-up price.
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  it('reports the measured round trip of a probe that answers', async () => {
    (testModelRuntime as jest.Mock).mockResolvedValueOnce({
      provider: 'openai',
      is_local: false,
      runtime_available: true,
      available_models: [],
      runtime_error: null,
    });

    render(<ModelCatalogue catalog={catalog} />);
    fireEvent.click(screen.getAllByRole('button', { name: 'Test' })[0]);

    await waitFor(() => {
      expect(testModelRuntime).toHaveBeenCalledWith('openai');
      expect(screen.getByText(/ok · \d+ ms/)).toBeInTheDocument();
    });
  });

  it('says that a key is missing when the provider has none', async () => {
    (testModelRuntime as jest.Mock).mockResolvedValueOnce({
      provider: 'openai',
      is_local: false,
      runtime_available: false,
      available_models: [],
      runtime_error: 'API key not provided',
    });

    render(<ModelCatalogue catalog={catalog} />);
    fireEvent.click(screen.getAllByRole('button', { name: 'Test' })[0]);

    await waitFor(() => {
      expect(screen.getByText('no key set')).toBeInTheDocument();
    });
  });

  it('carries the failure the API reported', async () => {
    (testModelRuntime as jest.Mock).mockRejectedValueOnce(new Error('Network down'));

    render(<ModelCatalogue catalog={catalog} />);
    fireEvent.click(screen.getAllByRole('button', { name: 'Test' })[0]);

    await waitFor(() => {
      expect(screen.getByText('Network down')).toBeInTheDocument();
    });
  });

  it('says that the catalogue is empty rather than drawing an empty row', () => {
    render(<ModelCatalogue catalog={[]} />);
    expect(screen.getByText('No models are configured on this deployment.')).toBeInTheDocument();
  });
});
