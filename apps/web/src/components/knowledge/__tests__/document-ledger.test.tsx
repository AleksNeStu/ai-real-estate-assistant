import { fireEvent, render, screen } from '@testing-library/react';

import { DocumentLedger } from '../document-ledger';

/**
 * The files waiting to be uploaded, and the state of the index.
 *
 * The ledger states what the API reports and nothing else: the API cannot
 * list the indexed documents, so the ledger must not pretend to.
 */
describe('DocumentLedger', () => {
  it('says so when no file is waiting', () => {
    render(
      <DocumentLedger
        files={[]}
        chunksIndexed={0}
        documentsRemaining={null}
        onRemove={() => {}}
      />
    );

    expect(screen.getByText('No file is waiting to be uploaded.')).toBeInTheDocument();
    expect(screen.getByText('0 files')).toBeInTheDocument();
  });

  it('names every file with its kind and its size', () => {
    render(
      <DocumentLedger
        files={[
          { name: 'umowa.pdf', size: 2 * 1024 * 1024, type: 'application/pdf' },
          { name: 'notatki.md', size: 900, type: 'text/markdown' },
        ]}
        chunksIndexed={18}
        documentsRemaining={null}
        onRemove={() => {}}
      />
    );

    expect(screen.getByText('umowa.pdf')).toBeInTheDocument();
    expect(screen.getByText('pdf · 2.0 MB')).toBeInTheDocument();
    expect(screen.getByText('notatki.md')).toBeInTheDocument();
    expect(screen.getByText('md · 900 B')).toBeInTheDocument();
    expect(screen.getByText('2 files')).toBeInTheDocument();
  });

  it('removes the file it was asked to remove', () => {
    const onRemove = jest.fn();
    render(
      <DocumentLedger
        files={[
          { name: 'a.pdf', size: 10, type: 'application/pdf' },
          { name: 'b.pdf', size: 10, type: 'application/pdf' },
        ]}
        chunksIndexed={0}
        documentsRemaining={null}
        onRemove={onRemove}
      />
    );

    const removeButtons = screen.getAllByRole('button', { name: 'Remove' });
    fireEvent.click(removeButtons[1]);

    expect(onRemove).toHaveBeenCalledWith(1);
  });

  it('states the two numbers the index reports', () => {
    const { rerender } = render(
      <DocumentLedger
        files={[]}
        chunksIndexed={18}
        documentsRemaining={null}
        onRemove={() => {}}
      />
    );

    expect(screen.getByText('Chunks indexed')).toBeInTheDocument();
    expect(screen.getByText('18')).toBeInTheDocument();
    // The count of the documents is only known after a clear.
    expect(screen.getByText('—')).toBeInTheDocument();

    rerender(
      <DocumentLedger
        files={[]}
        chunksIndexed={0}
        documentsRemaining={4}
        onRemove={() => {}}
      />
    );

    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.queryByText('—')).not.toBeInTheDocument();
  });
});
