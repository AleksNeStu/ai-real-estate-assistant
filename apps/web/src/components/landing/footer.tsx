import { getTranslations } from 'next-intl/server';

import { BuildMetadata } from '@/components/layout/build-metadata';
import { LANDING_SLOTS, withSlot, withUtm } from '@/lib/utm';

/**
 * The footer of the landing.
 *
 * Four columns: what this is, where to use it, where the code is, and who
 * stands behind it. The studio column carries the two products that exist -
 * the hosted version and the studio.
 */
export async function LandingFooter({ locale }: { locale: string }) {
  const t = await getTranslations('landing');

  const product = [
    { label: t('footer.productLiveDemo'), href: withSlot(`/${locale}/search`, 'footer') },
    { label: t('footer.productAssistant'), href: withSlot(`/${locale}/chat`, 'footer') },
    { label: t('footer.productCityOverview'), href: withSlot(`/${locale}/city-overview`, 'footer') },
    { label: t('footer.productAgents'), href: withSlot(`/${locale}/agents`, 'footer') },
  ];

  const openSource = [
    {
      label: t('footer.openSourceGithub'),
      href: withUtm('https://github.com/AleksNeStu/ai-real-estate-assistant', {
        medium: 'landing',
        campaign: 'oss',
        content: LANDING_SLOTS.footer,
      }),
      external: true,
    },
    {
      label: t('footer.openSourceDocs'),
      href: withUtm(
        'https://github.com/AleksNeStu/ai-real-estate-assistant/blob/main/docs/development/QUICKSTART_5MIN.md',
        { medium: 'landing', campaign: 'oss', content: 'footer_docs' }
      ),
      external: true,
    },
    {
      label: t('footer.openSourceDiscussions'),
      href: withUtm('https://github.com/AleksNeStu/ai-real-estate-assistant/discussions', {
        medium: 'landing',
        campaign: 'oss',
        content: 'footer',
      }),
      external: true,
    },
  ];

  const studio = [
    {
      label: t('footer.studioPropVector'),
      href: withUtm('https://propvectorai.com/', {
        medium: 'landing',
        campaign: 'propvector',
        content: 'footer',
      }),
      external: true,
    },
    {
      label: t('footer.studioNestLab'),
      href: withUtm('https://nestlab.tech/', {
        medium: 'landing',
        campaign: 'studio',
        content: 'footer',
      }),
      external: true,
    },
    {
      label: t('footer.studioServices'),
      href: withUtm('https://nestlab.tech/services', {
        medium: 'landing',
        campaign: 'studio',
        content: 'footer',
      }),
      external: true,
    },
  ];

  const columns = [
    { title: t('footer.product'), links: product },
    { title: t('footer.openSource'), links: openSource },
    { title: t('footer.studio'), links: studio },
  ];

  return (
    <footer className="border-t border-border">
      <div className="mx-auto grid max-w-[1248px] grid-cols-1 gap-10 px-6 pb-8 pt-12 text-[14px] leading-[22px] md:grid-cols-[minmax(0,1.5fr)_repeat(3,minmax(0,1fr))]">
        <div className="flex flex-col gap-3">
          <span className="font-semibold">{t('footer.brand')}</span>
          <span className="max-w-[320px] text-muted-foreground">{t('footer.tagline')}</span>
          <span className="inline-flex w-fit self-start items-stretch overflow-hidden rounded-[4px] border border-border font-mono text-[12px] font-medium">
            <span className="bg-foreground px-2 py-0.5 text-background">{t('footer.licenceLabel')}</span>
            <span className="px-2 py-0.5">{t('footer.licence')}</span>
          </span>
        </div>

        {columns.map((column) => (
          <div key={column.title} className="flex flex-col gap-1.5">
            <span className="mb-1 font-semibold">{column.title}</span>
            {column.links.map((link) => (
              <a
                key={link.label}
                href={link.href}
                {...('external' in link && link.external
                  ? { target: '_blank', rel: 'noreferrer' }
                  : {})}
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
          </div>
        ))}
      </div>

      <div className="mx-auto flex max-w-[1248px] flex-col gap-1 border-t border-border px-6 pb-16 pt-3.5 text-[12px] text-muted-foreground sm:flex-row sm:justify-between">
        <span>{t('footer.bottom')}</span>
        <span className="font-mono">{t('footer.locales')}</span>
      </div>

      <div className="mx-auto max-w-[1248px] border-t border-border px-6 pb-16 pt-3.5">
        <BuildMetadata />
      </div>
    </footer>
  );
}
