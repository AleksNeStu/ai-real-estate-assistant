import { getTranslations } from 'next-intl/server';

import { WaitlistForm } from '@/components/landing/waitlist-form';
import { OutboundLink } from '@/components/shell/outbound-link';
import { LANDING_SLOTS, withUtm } from '@/lib/utm';

/**
 * The hosted tier.
 *
 * The commercial path of the product, told in the product's own flow: what it
 * costs, when it launches and the one field that reaches the studio. It sits
 * high on the landing because it answers the question every visitor arrives
 * with - "who runs this for me" - and the open-source material belongs
 * further down the page.
 */
export async function HostedTier() {
  const t = await getTranslations('landing');

  return (
    <section id="hosted" className="mx-auto max-w-[1248px] scroll-mt-16 px-6 pt-24">
      <div className="mb-8 flex max-w-[760px] flex-col gap-3">
        <h2 className="text-section font-semibold">{t('exits.hosted.title')}</h2>
        <p className="text-muted-foreground">{t('exits.hosted.body')}</p>
      </div>

      <div className="grid grid-cols-1 overflow-hidden rounded-lg border border-border bg-muted lg:grid-cols-2">
        <div className="flex flex-col gap-5 p-6">
          <span className="font-mono text-[12px] font-medium text-warning">
            {t('exits.hosted.badge')}
          </span>

          <table className="text-[13px]">
            <tbody>
              {[
                [t('exits.hosted.priceFree'), t('exits.hosted.priceFreeValue')],
                [t('exits.hosted.pricePro'), t('exits.hosted.priceProValue')],
                [t('exits.hosted.priceEnterprise'), t('exits.hosted.priceEnterpriseValue')],
              ].map(([label, value], index) => (
                <tr key={label} className={index === 2 ? 'border-y border-border' : 'border-t border-border'}>
                  <td className="py-[7px]">{label}</td>
                  <td className="py-[7px] text-right font-mono text-[13px] font-semibold">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <OutboundLink
            outboundTarget="propvector"
            campaign="propvector"
            slot={LANDING_SLOTS.exitHosted}
            href={withUtm('https://propvectorai.com/', {
              medium: 'landing',
              campaign: 'propvector',
              content: LANDING_SLOTS.exitHosted,
            })}
            target="_blank"
            rel="noreferrer"
            className="text-[13px] font-medium text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            {t('exits.hosted.link')} ↗
          </OutboundLink>
        </div>

        <div className="flex flex-col justify-end gap-3.5 border-t border-border p-6 lg:border-l lg:border-t-0">
          <WaitlistForm />
        </div>
      </div>
    </section>
  );
}
