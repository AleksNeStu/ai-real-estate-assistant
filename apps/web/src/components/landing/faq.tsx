import { getTranslations } from 'next-intl/server';

import { LANDING_SLOTS, withUtm } from '@/lib/utm';

/**
 * The FAQ.
 *
 * Six questions, answered the way the README answers them. The answers were
 * already written - they only had to be rendered.
 */
export async function Faq() {
  const t = await getTranslations('landing');
  const questions = [1, 2, 3, 4, 5, 6];

  return (
    <section id="faq" className="mx-auto max-w-[1248px] scroll-mt-16 px-6 pb-28 pt-24">
      <div className="grid grid-cols-1 gap-14 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="flex flex-col gap-3">
          <h2 className="text-section font-semibold">{t('faq.title')}</h2>
          <a
            href={withUtm('https://github.com/AleksNeStu/ai-real-estate-assistant/discussions', {
              medium: 'landing',
              campaign: 'oss',
              content: LANDING_SLOTS.faqAsk,
            })}
            target="_blank"
            rel="noreferrer"
            className="text-[14px] font-medium text-foreground hover:underline"
          >
            {t('faq.ask')} →
          </a>
        </div>

        <div className="border-t border-foreground">
          {questions.map((index) => (
            <details key={index} className="group border-b border-border" open={index === 1}>
              <summary className="flex cursor-pointer list-none items-center justify-between gap-6 py-[18px] text-[17px] font-medium">
                {t(`faq.q${index}`)}
                <span className="font-mono text-[18px] text-muted-foreground transition-transform group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="m-0 pr-14 pb-5 text-muted-foreground">{t(`faq.a${index}`)}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
