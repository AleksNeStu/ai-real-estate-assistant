import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import { DocumentList } from '../document-list';
import { deleteDocument } from '@/lib/api';
import type { Document } from '@/lib/types';

jest.mock('@/lib/api', () => ({
  deleteDocument: jest.fn(),
  getDocumentDownloadUrl: (id: string) => `/api/v1/documents/${id}/download`,
}));

const mockDeleteDocument = deleteDocument as jest.Mock;

const soon = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
const later = new Date(Date.now() + 300 * 24 * 60 * 60 * 1000).toISOString();

const documents: Document[] = [
  {
    id: 'doc-1',
    user_id: 'user-1',
    original_filename: 'umowa-przedwstepna.pdf',
    filename: 'unique-umowa.pdf',
    file_type: 'application/pdf',
    file_size: 1024 * 412,
    category: 'contract',
    tags: ['important'],
    description: 'Sales contract',
    property_id: 'prop-1',
    expiry_date: soon,
    ocr_status: 'completed',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'doc-2',
    user_id: 'user-1',
    original_filename: 'wspolnota-regulamin.pdf',
    filename: 'unique-regulamin.pdf',
    file_type: 'application/pdf',
    file_size: 1024 * 96,
    category: 'other',
    tags: [],
    description: '',
    property_id: undefined,
    expiry_date: later,
    ocr_status: 'completed',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

describe('DocumentList', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockDeleteDocument.mockResolvedValue(undefined);
  });

  it('draws the files as rows of a ledger', () => {
    render(<DocumentList documents={documents} />);

    expect(screen.getByText('umowa-przedwstepna.pdf')).toBeInTheDocument();
    expect(screen.getByText('wspolnota-regulamin.pdf')).toBeInTheDocument();
    // The size is a number, so it is written in mono.
    expect(screen.getByText('412.0 KB')).toBeInTheDocument();
    expect(screen.getByText('96.0 KB')).toBeInTheDocument();
    // The property is an id - the API carries no address for it.
    expect(screen.getByText('prop-1')).toBeInTheDocument();
  });

  it('says how many days a file has left when it expires soon', () => {
    render(<DocumentList documents={documents} />);

    const expiryCell = screen.getByText(/· 7 d$/);
    expect(expiryCell).toBeInTheDocument();
    expect(expiryCell).toHaveClass('text-warning');
  });

  it('asks before it removes a file', async () => {
    const onDocumentDeleted = jest.fn();
    render(<DocumentList documents={documents} onDocumentDeleted={onDocumentDeleted} />);

    // The first press asks.
    fireEvent.click(screen.getByLabelText('Delete umowa-przedwstepna.pdf'));
    expect(mockDeleteDocument).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Confirm umowa-przedwstepna.pdf')).toBeInTheDocument();

    // The second one removes.
    fireEvent.click(screen.getByLabelText('Confirm umowa-przedwstepna.pdf'));

    await waitFor(() => {
      expect(mockDeleteDocument).toHaveBeenCalledWith('doc-1');
    });
    expect(onDocumentDeleted).toHaveBeenCalledWith('doc-1');
  });

  it('narrows the list by the category', () => {
    render(<DocumentList documents={documents} />);

    fireEvent.change(screen.getByRole('combobox', { name: /filter by category/i }), {
      target: { value: 'contract' },
    });

    expect(screen.getByText('umowa-przedwstepna.pdf')).toBeInTheDocument();
    expect(screen.queryByText('wspolnota-regulamin.pdf')).not.toBeInTheDocument();
  });

  it('narrows the list by the search', () => {
    render(<DocumentList documents={documents} />);

    fireEvent.change(screen.getByLabelText('Search documents'), {
      target: { value: 'regulamin' },
    });

    expect(screen.getByText('wspolnota-regulamin.pdf')).toBeInTheDocument();
    expect(screen.queryByText('umowa-przedwstepna.pdf')).not.toBeInTheDocument();
  });
});
