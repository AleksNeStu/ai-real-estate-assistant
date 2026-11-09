/**
 * Register Page Object for E2E tests.
 * Encapsulates registration page interactions and elements.
 */

import { Page, Locator, expect } from '@playwright/test';

export class RegisterPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly fullNameInput: Locator;
  readonly consentCheckbox: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;
  readonly successMessage: Locator;
  readonly loginLink: Locator;

  constructor(page: Page) {
    this.page = page;
    // Actual UI: inputs with labels "Email", "Password", "Full Name".
    // The names have to match exactly: the footer carries a newsletter field
    // labelled "Email address", and a loose match collects that one as well -
    // two elements, and every action on them fails the strict mode.
    this.emailInput = page
      .getByLabel('Email', { exact: true })
      .or(page.getByRole('textbox', { name: /^email$/i }));
    this.passwordInput = page
      .getByLabel('Password', { exact: true })
      .or(page.getByRole('textbox', { name: /^password$/i }));
    // Note: No confirm password field in actual UI
    this.fullNameInput = page
      .getByLabel('Full Name', { exact: true })
      .or(page.getByRole('textbox', { name: /^full name$/i }));
    // The consent box. The registration form refuses to submit without it -
    // the backend writes `gdpr_consent_at` from it, so a form without it
    // would create an account with no record of the consent. A test that
    // registers a user ticks it, exactly as a person does.
    this.consentCheckbox = page.locator('#consent, input[name="consent"]');
    // Submit button text is "Create Account" - must be inside the form of the
    // registration, the footer newsletter has a form with a submit button of
    // its own.
    const registerForm = page.locator('form').filter({ has: page.locator('#email') });
    this.submitButton = registerForm
      .locator('button[type="submit"]')
      .or(
        page
          .locator('button[type="submit"]')
          .filter({ hasText: /create account|sign up|register|zarejestruj/i })
      );
    // Error message is in a div with bg-destructive/15 class - be specific to avoid matching Next.js route announcer
    this.errorMessage = page
      .locator('.bg-destructive\\/15, .text-destructive')
      .filter({ has: page.locator('svg, span, p') })
      .first();
    this.successMessage = page.locator('[data-testid="success-message"], .success-message');
    // The link to the login - the navigation carries a link of its own, so the
    // one of the card is picked by its underlined class.
    this.loginLink = page
      .locator('a.underline')
      .filter({ hasText: /sign in|log in|zaloguj|зарегистрироваться/i })
      .first();
  }

  /**
   * Navigate to the registration page.
   */
  async navigate(): Promise<void> {
    await this.page.goto('/auth/register');
    // Wait for the form to be visible
    await expect(this.emailInput).toBeVisible({ timeout: 10000 });
  }

  /**
   * Fill the registration form.
   */
  async fillForm(options: {
    email: string;
    password: string;
    fullName?: string;
    confirmPassword?: string; // Kept for API compatibility but ignored (no confirm field in UI)
  }): Promise<void> {
    await this.emailInput.fill(options.email);
    await this.passwordInput.fill(options.password);

    if (options.fullName) {
      await this.fullNameInput.fill(options.fullName);
    }
    // The consent is required by the form: without it the submit is refused
    // and the account is never created. A person ticks it, so a test does.
    await this.consentCheckbox.check();
    // Note: confirmPassword is ignored - actual UI doesn't have this field
  }

  /**
   * Submit the registration form.
   */
  async submit(): Promise<void> {
    await this.submitButton.click();
  }

  /**
   * Perform a complete registration action.
   */
  async register(options: {
    email: string;
    password: string;
    fullName?: string;
    confirmPassword?: string;
  }): Promise<void> {
    await this.fillForm(options);
    await this.submit();
  }

  /**
   * Wait for registration to complete.
   */
  async waitForRegistrationSuccess(): Promise<void> {
    // Wait for success message or redirect
    await Promise.race([
      expect(this.successMessage).toBeVisible({ timeout: 10000 }),
      this.page.waitForURL(/^(?!.*\/auth\/register).*$/, { timeout: 10000 }),
    ]);
  }

  /**
   * Wait for error message to appear.
   */
  async waitForError(): Promise<string> {
    await expect(this.errorMessage).toBeVisible({ timeout: 5000 });
    return (await this.errorMessage.textContent()) || '';
  }

  /**
   * Check if error message is visible.
   */
  async hasError(): Promise<boolean> {
    return await this.errorMessage.isVisible();
  }

  /**
   * Click the login link.
   */
  async clickLogin(): Promise<void> {
    await this.loginLink.click();
  }
}
