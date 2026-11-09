'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { buildHeaders, getApiUrl } from '@/lib/api/client';
import { getOrCreateVisitorId } from '@/lib/visitor-tracking';
import { reportOutbound } from '@/lib/attribution';
import { LANDING_SLOTS } from '@/lib/utm';

/**
 * The PropVector AI waitlist.
 *
 * The address goes into the same lead pipeline the footer's form uses, with
 * its own source, so the studio can tell a waitlist signup from an ordinary
 * contact. The promise depends on what the deployment can actually do: if
 * there is no mail sender, the form says the address is noted and stops
 * there - it never promises an e-mail that will not arrive.
 */

type SubmitState = 'idle' | 'loading' | 'success' | 'error';

export function WaitlistForm() {
  const t = useTranslations('landing');
  const [email, setEmail] = useState('');
  const [state, setState] = useState<SubmitState>('idle');
  const [canMail, setCanMail] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch(`${getApiUrl()}/capabilities`, { headers: buildHeaders() });
        if (!response.ok) throw new Error('capabilities failed');
        const capabilities = (await response.json()) as {
          lead_capture?: { waitlist_enabled?: boolean };
        };
        if (!cancelled) setCanMail(Boolean(capabilities.lead_capture?.waitlist_enabled));
      } catch {
        // Without the capabilities we make no promise about an e-mail.
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) {
      setState('error');
      return;
    }

    setState('loading');
    try {
      const response = await fetch(`${getApiUrl()}/leads/visitor`, {
        method: 'POST',
        headers: buildHeaders(),
        body: JSON.stringify({
          visitor_id: getOrCreateVisitorId(),
          email: trimmed,
          source: 'propvector_waitlist',
          consent_given: true,
        }),
      });
      if (!response.ok) throw new Error(`waitlist failed: ${response.status}`);
      setState('success');
      setEmail('');
      void reportOutbound('propvector', LANDING_SLOTS.waitlist, 'propvector');
    } catch {
      setState('error');
    }
  }

  if (state === 'success') {
    return (
      <span className="text-[14px] text-success">
        {canMail ? t('exits.hosted.waitlistSuccess') : t('exits.hosted.waitlistHint')}
      </span>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-1.5" noValidate>
      <div className="flex gap-1.5">
        <label htmlFor="waitlist-email" className="sr-only">
          {t('exits.hosted.waitlistLabel')}
        </label>
        <input
          id="waitlist-email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder={t('exits.hosted.waitlistPlaceholder')}
          aria-label={t('exits.hosted.waitlistLabel')}
          aria-invalid={state === 'error' ? 'true' : undefined}
          className={`h-10 flex-1 rounded-md border bg-background px-2.5 text-[14px] text-foreground outline-none placeholder:text-muted-foreground ${
            state === 'error' ? 'border-destructive' : 'border-border'
          }`}
        />
        <button
          type="submit"
          disabled={state === 'loading'}
          className="h-10 rounded-md bg-foreground px-3.5 text-[14px] font-medium text-background transition-colors hover:bg-foreground/90 disabled:opacity-60"
        >
          {t('exits.hosted.waitlistSubmit')}
        </button>
      </div>
      <span className={`text-[12px] ${state === 'error' ? 'text-destructive' : 'text-muted-foreground'}`}>
        {state === 'error'
          ? t('exits.hosted.waitlistInvalid')
          : canMail
            ? t('exits.hosted.waitlistHint')
            : t('exits.hosted.waitlistNoteNoMail')}
      </span>
    </form>
  );
}
