/**
 * Tests for CMA (Comparative Market Analysis) page.
 *
 * Tests for the CMA page wrapper including:
 * - Page heading and description
 * - CMAWizard component rendering (wizard steps visible)
 * - Search input presence
 * - Step navigation structure
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import CMAPage from '../page';

// Mock next-intl to return keys as display text
jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

describe('CMAPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the page heading', () => {
    render(<CMAPage />);
    expect(screen.getByText('Comparative Market Analysis')).toBeInTheDocument();
  });

  it('renders the page description', () => {
    render(<CMAPage />);
    expect(
      screen.getByText(
        'Generate professional CMA reports by selecting a subject property and comparable listings.'
      )
    ).toBeInTheDocument();
  });

  it('renders the CMAWizard step navigation', () => {
    render(<CMAPage />);
    // The wizard numbers the five steps on the rule (01-05)
    expect(screen.getByText('01')).toBeInTheDocument();
    expect(screen.getByText('02')).toBeInTheDocument();
    expect(screen.getByText('03')).toBeInTheDocument();
    expect(screen.getByText('04')).toBeInTheDocument();
    expect(screen.getByText('05')).toBeInTheDocument();
  });

  it('renders search input from the wizard', () => {
    render(<CMAPage />);
    const searchInput = screen.getByRole('textbox');
    expect(searchInput).toBeInTheDocument();
    expect(searchInput).toHaveAttribute('placeholder', 'Search by address, city or title...');
  });

  it('renders correct page structure with h1', () => {
    const { container } = render(<CMAPage />);
    const heading = container.querySelector('h1');
    expect(heading).toBeInTheDocument();
    expect(heading?.textContent).toBe('Comparative Market Analysis');
  });
});
