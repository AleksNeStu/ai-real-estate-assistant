import { render, screen } from '@testing-library/react';

import {
  AuthCard,
  AuthDivider,
  AuthField,
  AuthHeading,
  AuthLinks,
  AuthNote,
  AuthStatus,
} from '../auth-shell';

/**
 * The shell of the six auth screens.
 *
 * The tests read the rendered output: the card's measure, the heading, the
 * field's label and hint, the divider, the status line's tone and the note.
 */
describe('the auth shell', () => {
  it('renders the card at the 380px measure', () => {
    render(<AuthCard>content</AuthCard>);
    expect(screen.getByTestId('auth-card')).toHaveClass('max-w-[380px]');
  });

  it('renders the heading as the only h1 of the screen', () => {
    render(<AuthHeading title="Sign in" description="To your favourites." />);

    const heading = screen.getByRole('heading', { level: 1, name: 'Sign in' });
    expect(heading).toBeInTheDocument();
    expect(screen.getByText('To your favourites.')).toBeInTheDocument();
  });

  it('names the control by its label and keeps the hint out of the name', () => {
    render(
      <AuthField label="Password" htmlFor="password" hint={<a href="/x">Forgot?</a>}>
        <input id="password" type="password" />
      </AuthField>
    );

    // The label names the control and nothing else - a hint inside the
    // label would change the control's accessible name.
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByText('Forgot?')).toBeInTheDocument();
  });

  it('renders the divider as two hairlines and a word', () => {
    render(<AuthDivider label="or with e-mail" />);
    expect(screen.getByText('or with e-mail')).toBeInTheDocument();
  });

  it('renders the status line with a dot of its tone', () => {
    render(<AuthStatus tone="warning">The link is in the API log.</AuthStatus>);

    expect(screen.getByRole('status')).toHaveTextContent('The link is in the API log.');
    expect(screen.getByTestId('auth-status-dot')).toHaveClass('bg-warning');
  });

  it('renders the links row and the note', () => {
    render(
      <>
        <AuthLinks>
          <a href="/register">Create an account</a>
        </AuthLinks>
        <AuthNote>Accounts are part of this open-source repository.</AuthNote>
      </>
    );

    expect(screen.getByRole('link', { name: 'Create an account' })).toBeInTheDocument();
    expect(screen.getByText('Accounts are part of this open-source repository.')).toBeInTheDocument();
  });
});
