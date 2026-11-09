'use client';

import type { ReactNode } from 'react';

import { AccountGate } from '@/components/shell/gate';

/**
 * The gate on the `usage` routes.
 *
 * The page behind it needs an account. Rather than bouncing an anonymous
 * visitor to the login page and losing the context, the gate says what the
 * account gives and offers the two ways in.
 */
export default function UsageLayout({ children }: { children: ReactNode }) {
  return <AccountGate route="usage">{children}</AccountGate>;
}
