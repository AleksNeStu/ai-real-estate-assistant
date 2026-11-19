import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { BuyerMemorySettings } from '../buyer-memory-settings';
import { deleteBuyerMemory, getBuyerMemory } from '@/lib/api';
import { ApiError } from '@/lib/api/client';

// The API module is mocked, but the error class the component reads is the
// real one - the component tells an auth failure from another failure by it.
jest.mock('@/lib/api', () => ({
  ...jest.requireActual('@/lib/api'),
  getBuyerMemory: jest.fn(),
  deleteBuyerMemory: jest.fn(),
}));

const mockGetBuyerMemory = getBuyerMemory as jest.Mock;
const mockDeleteBuyerMemory = deleteBuyerMemory as jest.Mock;

const FACT = {
  id: 'fact-1',
  kind: 'budget',
  content: 'up to 500,000 PLN',
  listing_id: null,
  confidence: 0.9,
  source: 'chat',
  created_at: '2026-11-01T10:00:00Z',
  expires_at: '2027-11-01T10:00:00Z',
};

const DISLIKED_FACT = {
  ...FACT,
  id: 'fact-2',
  kind: 'disliked',
  content: 'the flat with the balcony',
};

describe('BuyerMemorySettings', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('lists what is remembered, fact by fact', async () => {
    mockGetBuyerMemory.mockResolvedValue({ facts: [FACT, DISLIKED_FACT], count: 2 });

    render(<BuyerMemorySettings />);

    expect(await screen.findByText('up to 500,000 PLN')).toBeInTheDocument();
    expect(screen.getByText('the flat with the balcony')).toBeInTheDocument();

    // The kind is named, so the reader knows what a fact is.
    expect(screen.getByText('Budget')).toBeInTheDocument();
    expect(screen.getByText('Listing you disliked')).toBeInTheDocument();
  });

  it('says that nothing is remembered when the memory is empty', async () => {
    mockGetBuyerMemory.mockResolvedValue({ facts: [], count: 0 });

    render(<BuyerMemorySettings />);

    expect(await screen.findByText('Nothing is remembered about you.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Delete the memory/i })).not.toBeInTheDocument();
  });

  it('says that the memory belongs to a signed-in account when it is not', async () => {
    mockGetBuyerMemory.mockRejectedValue(new ApiError('Not authenticated', 401));

    render(<BuyerMemorySettings />);

    expect(
      await screen.findByText('The memory belongs to a signed-in account.')
    ).toBeInTheDocument();
  });

  it('asks first, and deletes nothing until the visitor confirms', async () => {
    mockGetBuyerMemory.mockResolvedValue({ facts: [FACT], count: 1 });
    mockDeleteBuyerMemory.mockResolvedValue({ deleted: 1 });

    render(<BuyerMemorySettings />);

    await screen.findByText('up to 500,000 PLN');

    fireEvent.click(screen.getByRole('button', { name: /Delete the memory/i }));

    // The confirmation asks, and nothing has been erased yet.
    expect(await screen.findByText('Delete the buyer memory?')).toBeInTheDocument();
    expect(mockDeleteBuyerMemory).not.toHaveBeenCalled();

    // Cancelling closes the question and leaves the memory alone.
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    await waitFor(() => {
      expect(screen.queryByText('Delete the buyer memory?')).not.toBeInTheDocument();
    });
    expect(mockDeleteBuyerMemory).not.toHaveBeenCalled();
  });

  it('erases the memory on confirmation and says that it is gone', async () => {
    mockGetBuyerMemory.mockResolvedValue({ facts: [FACT], count: 1 });
    mockDeleteBuyerMemory.mockResolvedValue({ deleted: 1 });

    render(<BuyerMemorySettings />);

    await screen.findByText('up to 500,000 PLN');

    fireEvent.click(screen.getByRole('button', { name: /Delete the memory/i }));
    fireEvent.click(await screen.findByRole('button', { name: 'Delete it' }));

    await waitFor(() => {
      expect(mockDeleteBuyerMemory).toHaveBeenCalledTimes(1);
    });

    // The fact is gone and the visitor is told so.
    await waitFor(() => {
      expect(screen.queryByText('up to 500,000 PLN')).not.toBeInTheDocument();
    });
    expect(screen.getByText('1 fact deleted')).toBeInTheDocument();
    expect(screen.getByText('Nothing is remembered about you.')).toBeInTheDocument();
  });

  it('keeps the facts and says the erasure failed when the server refuses', async () => {
    mockGetBuyerMemory.mockResolvedValue({ facts: [FACT], count: 1 });
    mockDeleteBuyerMemory.mockRejectedValue(new ApiError('Internal server error', 500));

    render(<BuyerMemorySettings />);

    await screen.findByText('up to 500,000 PLN');

    fireEvent.click(screen.getByRole('button', { name: /Delete the memory/i }));
    fireEvent.click(await screen.findByRole('button', { name: 'Delete it' }));

    await waitFor(() => {
      expect(screen.getByText('Internal server error')).toBeInTheDocument();
    });
    expect(screen.getByText('up to 500,000 PLN')).toBeInTheDocument();
  });

  it('offers a retry when the memory cannot be read', async () => {
    mockGetBuyerMemory.mockRejectedValueOnce(new ApiError('Internal server error', 500));
    mockGetBuyerMemory.mockResolvedValueOnce({ facts: [FACT], count: 1 });

    render(<BuyerMemorySettings />);

    const retry = await screen.findByRole('button', { name: 'Retry' });
    fireEvent.click(retry);

    expect(await screen.findByText('up to 500,000 PLN')).toBeInTheDocument();
  });
});
