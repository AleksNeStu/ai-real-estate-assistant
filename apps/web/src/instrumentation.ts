/**
 * Sentry for the server runtime.
 *
 * The Next.js server renders the pages and proxies the API calls. When one
 * of them throws, the stack trace used to stay in the container's stdout,
 * where it was lost on the next restart.
 *
 * The DSN is a server-side value: without it nothing is initialized.
 */
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME !== 'nodejs') {
    return;
  }

  const dsn = process.env.SENTRY_DSN ?? process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn) {
    return;
  }

  const Sentry = await import('@sentry/nextjs');

  Sentry.init({
    dsn,
    environment:
      process.env.SENTRY_ENVIRONMENT ??
      process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ??
      process.env.NODE_ENV,
    tracesSampleRate: 0.1,
    sendDefaultPii: false,
  });
}
