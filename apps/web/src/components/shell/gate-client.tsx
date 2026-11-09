'use client';

import { useTranslations } from 'next-intl';

/**
 * The "Preview signed-in state" escape hatch of the gate.
 *
 * On a demo deployment the account routes are worth looking at before anyone
 * signs in - the design is a part of the product, and the operator wants to
 * see the pages the way a signed-in visitor gets them. The flag is a plain
 * localStorage key, so it changes what the browser shows and nothing else:
 * no account is created, no server state is touched.
 *
 * The button is only offered when the deployment is a demo.
 */

const PREVIEW_KEY = 're2-auth';

export function GatePreview() {
  const t = useTranslations('gate');

  if (process.env.NEXT_PUBLIC_DEMO_MODE !== 'true') {
    return null;
  }

  return (
    <button
      type="button"
      onClick={() => {
        window.localStorage.setItem(PREVIEW_KEY, '1');
        window.location.reload();
      }}
      className="border-0 bg-transparent px-3 py-0 text-[13px] text-muted-foreground underline underline-offset-[3px] transition-colors hover:text-foreground"
    >
      {t('preview')}
    </button>
  );
}
