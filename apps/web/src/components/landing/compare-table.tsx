import { getTranslations } from 'next-intl/server';

/**
 * The comparison table.
 *
 * Four states, and the difference between them is the whole point: what is in
 * this repository, what in it needs an account, what in it needs your own
 * key, and what only the hosted tier has.
 */
const STATE_DOT: Record<string, string> = {
  inRepo: 'bg-success',
  account: 'bg-foreground',
  key: 'bg-warning',
  hosted: 'border border-muted-foreground bg-transparent',
};

export async function CompareTable() {
  const t = await getTranslations('landing');
  const rows = t.raw('compare.rows') as {
    cap: string;
    repo: string;
    repoState: string;
    pv: string;
  }[];

  const legend = [
    { label: t('compare.legendInRepo'), dot: 'bg-success' },
    { label: t('compare.legendAccount'), dot: 'bg-foreground' },
    { label: t('compare.legendKey'), dot: 'bg-warning' },
    { label: t('compare.legendHosted'), dot: 'border border-muted-foreground bg-transparent' },
  ];

  return (
    <section id="compare" className="mx-auto max-w-[1248px] scroll-mt-16 px-6 pt-24">
      <div className="grid grid-cols-1 gap-14 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="flex flex-col gap-3">
          <h2 className="text-section font-semibold">{t('compare.title')}</h2>
          <p className="text-muted-foreground">{t('compare.body')}</p>
          <div className="mt-2 flex flex-col gap-1.5 text-[13px]">
            {legend.map((entry) => (
              <span key={entry.label} className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${entry.dot}`} />
                {entry.label}
              </span>
            ))}
          </div>
        </div>

        <div>
          <table className="w-full border-collapse text-[14px]">
            <thead>
              <tr className="border-b border-foreground text-left">
                <th className="py-2.5 text-[13px] font-medium text-muted-foreground">
                  {t('compare.columnCapability')}
                </th>
                <th className="w-[260px] py-2.5 font-semibold">{t('compare.columnRepo')}</th>
                <th className="w-[200px] py-2.5 font-semibold">{t('compare.columnHosted')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.cap} className="border-b border-border">
                  <td className="py-2.5 pr-4">{row.cap}</td>
                  <td className="py-2.5">
                    <span className="inline-flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${STATE_DOT[row.repoState] ?? 'bg-foreground'}`} />
                      <span>{row.repo}</span>
                    </span>
                  </td>
                  <td className="py-2.5 text-[13px]">{row.pv}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="mt-3.5 flex items-baseline justify-between gap-6">
            <span className="font-mono text-[13px] font-medium">{t('compare.noteLeft')}</span>
            <span className="text-[13px] text-muted-foreground">{t('compare.noteRight')}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
