'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { buildHeaders, getApiUrl } from '@/lib/api/client';

/**
 * The data and coverage section.
 *
 * The numbers are the catalogue's own: the demo shows what it actually
 * holds, and the table says what a live provider would add, country by
 * country. Nothing here is typed in by hand.
 */

interface CatalogueStats {
  total: number;
  agents: number;
  cities: { name: string; count: number }[];
  currencies: string[];
}

const COVERAGE = [
  { name: 'Poland', sub: 'DE · ES · IT · PT · FR · …', yours: 'works', live: 'works', liveTone: 'ok' },
  { name: 'European Union', sub: 'DE · ES · IT · PT · FR · …', yours: 'planned', live: 'planned', liveTone: 'planned' },
  { name: 'United Kingdom', sub: '', yours: 'planned', live: 'planned', liveTone: 'planned' },
  { name: 'United States', sub: '', yours: 'planned', live: 'planned', liveTone: 'planned' },
  { name: 'Anywhere else', sub: 'a data source away', yours: 'planned', live: 'planned', liveTone: 'planned' },
] as const;

export function DataCoverage() {
  const t = useTranslations('landing');
  const [stats, setStats] = useState<CatalogueStats | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch(`${getApiUrl()}/catalogue/stats`, {
          headers: buildHeaders(),
        });
        if (!response.ok) throw new Error(`catalogue stats failed: ${response.status}`);
        const data = (await response.json()) as CatalogueStats;
        if (!cancelled) setStats(data);
      } catch {
        // The section still renders; the numbers stay empty.
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const cities = stats?.cities ?? [];
  const widest = Math.max(...cities.map((city) => city.count), 1);

  return (
    <section id="data" className="mx-auto max-w-[1248px] scroll-mt-16 px-6 pt-24">
      <div className="grid grid-cols-1 gap-14 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="flex flex-col gap-3">
          <h2 className="text-section font-semibold">{t('data.title')}</h2>
          <p className="text-muted-foreground">{t('data.body')}</p>
          <div className="mt-2 flex items-center gap-2 rounded-lg border border-border px-3 py-2.5 text-[13px] leading-[19px]">
            <span className="h-2 w-2 shrink-0 rounded-full bg-warning" />
            {t('data.noLiveFeed')}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
          <div className="flex flex-col gap-2.5">
            <div className="flex items-baseline justify-between">
              <span className="font-semibold">{t('data.catalogueTitle')}</span>
              <span className="font-mono text-[12px] text-muted-foreground">
                {stats
                  ? t('data.catalogueSummary', { count: stats.total, agents: stats.agents })
                  : '—'}
              </span>
            </div>
            <div className="border-t border-foreground">
              {cities.map((city) => (
                <div
                  key={city.name}
                  className="grid grid-cols-[90px_minmax(0,1fr)_40px] items-center gap-3 border-b border-border py-2 text-[14px]"
                >
                  <span>{city.name}</span>
                  <span
                    className="h-1.5 rounded-[1px] bg-foreground"
                    style={{ width: `${Math.max((city.count / widest) * 100, 4)}%` }}
                  />
                  <span className="text-right font-mono text-[13px] font-medium">{city.count}</span>
                </div>
              ))}
            </div>
            <span className="text-[12px] text-muted-foreground">{t('data.catalogueNote')}</span>
          </div>

          <div className="flex flex-col gap-2.5">
            <div className="flex items-baseline justify-between">
              <span className="font-semibold">{t('data.coverageTitle')}</span>
              <span className="font-mono text-[12px] text-muted-foreground">
                {t('data.coverageAsOf')}
              </span>
            </div>
            <div className="border-t border-foreground text-[13px]">
              <div className="grid grid-cols-[minmax(0,1fr)_92px_112px] gap-2.5 border-b border-border py-2 text-[12px] text-muted-foreground">
                <span>{t('data.coverageRegion')}</span>
                <span>{t('data.coverageYours')}</span>
                <span>{t('data.coverageLive')}</span>
              </div>
              {COVERAGE.map((row) => (
                <div
                  key={row.name}
                  className="grid grid-cols-[minmax(0,1fr)_92px_112px] items-center gap-2.5 border-b border-border py-2"
                >
                  <span className="flex flex-col">
                    <span>{row.name}</span>
                    {row.sub ? (
                      <span className="text-[11px] text-muted-foreground">{row.sub}</span>
                    ) : null}
                  </span>
                  <span className="flex items-center gap-1.5">
                    {row.yours === 'works' ? (
                      <span className="h-1.5 w-1.5 rounded-full bg-success" />
                    ) : null}
                    <span className={row.yours === 'works' ? '' : 'text-muted-foreground'}>
                      {row.yours}
                    </span>
                  </span>
                  <span className="flex items-center gap-1.5">
                    {row.liveTone === 'ok' ? (
                      <span className="h-1.5 w-1.5 rounded-full bg-success" />
                    ) : (
                      <span className="h-1.5 w-1.5 rounded-full border border-muted-foreground" />
                    )}
                    <span className={row.liveTone === 'ok' ? '' : 'text-muted-foreground'}>
                      {row.live}
                    </span>
                  </span>
                </div>
              ))}
            </div>
            <span className="text-[12px] text-muted-foreground">{t('data.coverageNote')}</span>

            <span className="mt-3 font-semibold">{t('data.adaptersTitle')}</span>
            <div className="flex flex-wrap gap-1.5">
              {(t.raw('data.adapters') as string[]).map((adapter) => (
                <span key={adapter} className="rounded-[4px] border border-border px-2 py-[3px] text-[13px]">
                  {adapter}
                </span>
              ))}
            </div>
            <span className="text-[12px] text-muted-foreground">{t('data.adaptersNote')}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
