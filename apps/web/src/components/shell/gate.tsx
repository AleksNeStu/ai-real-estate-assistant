'use client';

import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { useAuth } from '@/contexts/AuthContext';
import { getCapabilities } from '@/lib/api/capabilities';
import { useCapabilities } from '@/hooks/useCapabilities';
import { GatePreview } from './gate-client';

/**
 * The gate on the account routes.
 *
 * A route that belongs to an account is not a dead end for an anonymous
 * visitor: it says what the account gives you, and it offers the two ways in.
 * The proxy used to bounce these routes to the login page, which threw away
 * the context - the visitor arrived at `/favorites` and was told to sign in,
 * without ever hearing what a favourite is.
 *
 * The gate renders only when the deployment really needs an account. Two
 * answers decide that, and both come from the backend rather than from a
 * guess:
 *
 * - `auth.jwt_enabled` - a deployment without JWT has no accounts at all, so
 *   there is nothing to sign in to;
 * - `auth.demo_user_bypass` - a deployment that hands every visitor a
 *   synthetic user already lets them through, so a gate would be a lie.
 *
 * While the answer is still in flight the children render, so a signed-in
 * visitor never sees a flash of the gate.
 */

export interface AccountGateProps {
  /** The route key under `gate.routes` - `favorites`, `usage`, ... */
  route: string;
  children: ReactNode;
}

export function AccountGate({ route, children }: AccountGateProps) {
  const t = useTranslations('gate');
  const { isAuthenticated, isLoading } = useAuth();
  const { capabilities, loading } = useCapabilities();

  if (isLoading || loading || !capabilities) {
    return <>{children}</>;
  }

  if (isAuthenticated) {
    return <>{children}</>;
  }

  // A deployment without accounts, or one that lets everybody in, does not
  // need the gate.
  if (!capabilities.auth.jwt_enabled || capabilities.auth.demo_user_bypass) {
    return <>{children}</>;
  }

  const copy = t.raw(`routes.${route}`);
  const items = Array.isArray(copy?.items) ? (copy.items as string[]) : [];

  return (
    <div className="mx-auto grid max-w-[1200px] grid-cols-1 items-start gap-14 px-6 py-14 lg:grid-cols-[minmax(0,1fr)_420px]">
      <div className="flex flex-col gap-5">
        <span className="font-mono text-[12px] leading-4 text-muted-foreground">
          {t('eyebrow', { route: `/${route}` })}
        </span>
        <h1 className="m-0 text-[34px] font-semibold leading-10 tracking-[-0.03em]">
          {copy?.title}
        </h1>
        <p className="m-0 max-w-[560px] text-[16px] leading-[25px] text-muted-foreground">
          {copy?.what}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <a
            href="/auth/login"
            className="inline-flex h-10 items-center rounded-md bg-action px-[18px] text-[14px] font-medium text-action-foreground transition-colors hover:bg-action/90"
          >
            {t('signIn')}
          </a>
          <a
            href="/auth/register"
            className="inline-flex h-10 items-center rounded-md border border-border px-4 text-[14px] font-medium text-foreground transition-colors hover:bg-muted"
          >
            {t('createAccount')}
          </a>
          <GatePreview />
        </div>
        <p className="m-0 mt-2 max-w-[560px] text-[13px] leading-5 text-muted-foreground">
          {t('note', { link: 'PropVector AI' })}
        </p>
      </div>

      <div className="overflow-hidden rounded-lg border border-border">
        <div className="border-b border-border bg-muted px-3.5 py-2.5 font-mono text-[12px] leading-4 text-muted-foreground">
          {t('afterSignIn')}
        </div>
        {items.map((item) => (
          <div
            key={item}
            className="border-b border-border px-3.5 py-[11px] text-[14px] leading-5 last:border-b-0"
          >
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
