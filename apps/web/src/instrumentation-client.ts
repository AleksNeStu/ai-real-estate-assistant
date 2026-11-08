/**
 * Sentry for the browser.
 *
 * The Content Security Policy of the application already allows Sentry's
 * origins, but nothing ever sent an event: the SDK was never initialized in
 * the browser, so a page that threw left a stack trace only in the
 * developer's console - and, in production, nowhere at all.
 *
 * The DSN is a public value: it identifies the project, it does not grant
 * access to it. Without a DSN nothing is initialized and no request is
 * made - a deployment without error tracking stays silent.
 */
import * as Sentry from '@sentry/nextjs';

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
    tracesSampleRate: 0.1,
    // The catalogue holds the addresses and the prices of real homes: the
    // browser sends the stack trace, not the data of the visitor.
    sendDefaultPii: false,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
  });
}
