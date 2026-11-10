import { render, screen } from '@testing-library/react';

import { SettingsPanel, SettingsRow } from '../settings-panel';

/**
 * The two shapes every settings section is built from.
 *
 * The test is through the rendered output: the panel opens its rows with an
 * ink rule, and the row says what the thing is beside its value.
 */
describe('the settings panel', () => {
  it('states the section and what it is for', () => {
    render(
      <SettingsPanel title="Models" description="Every provider this deployment can reach.">
        <SettingsRow label="Chat" description="Conversational responses">
          <span>gpt-4o</span>
        </SettingsRow>
      </SettingsPanel>
    );

    expect(screen.getByRole('heading', { name: 'Models' })).toBeInTheDocument();
    expect(
      screen.getByText('Every provider this deployment can reach.')
    ).toBeInTheDocument();
  });

  it('puts the label beside the value', () => {
    render(
      <SettingsPanel title="Models">
        <SettingsRow label="Chat" description="Conversational responses">
          <span>gpt-4o</span>
        </SettingsRow>
      </SettingsPanel>
    );

    expect(screen.getByText('Chat')).toBeInTheDocument();
    expect(screen.getByText('Conversational responses')).toBeInTheDocument();
    expect(screen.getByText('gpt-4o')).toBeInTheDocument();
  });

  it('carries the action of the row', () => {
    render(
      <SettingsPanel title="Models">
        <SettingsRow label="Chat" action={<button type="button">Save</button>}>
          <span>gpt-4o</span>
        </SettingsRow>
      </SettingsPanel>
    );

    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
  });
});
