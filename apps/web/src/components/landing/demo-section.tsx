import { getTranslations } from 'next-intl/server';

import { DemoClip } from '@/components/landing/demo-clip';

/**
 * The six seconds of the demo.
 *
 * The section carries one thing: the clip. The file is played on the click,
 * so the landing keeps its budget and the page never calls the model - the
 * clip is a build-time asset, not a request.
 */
export async function DemoSection({ locale }: { locale: string }) {
  const t = await getTranslations('landing');

  return (
    <section id="demo" className="mx-auto max-w-[1248px] scroll-mt-16 px-6 pt-24">
      <div className="grid grid-cols-1 gap-14 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="flex flex-col gap-3">
          <h2 className="text-section font-semibold">{t('demo.title')}</h2>
          <p className="text-muted-foreground">{t('demo.body')}</p>
        </div>

        <DemoClip locale={locale} />
      </div>
    </section>
  );
}
