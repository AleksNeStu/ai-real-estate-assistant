'use client';

import { useTranslations } from 'next-intl';

/**
 * The filter pane of the agent directory.
 *
 * The prototype draws the filters as three groups of controls: the city and
 * the specialty as pills, the minimum rating as a four-cell segment, and the
 * sort as a list of rows in one frame. The pane is 248px wide, the same
 * width the search route gives its own filters, so the two routes feel like
 * one application.
 *
 * The state is held by the page; this component only reports what was
 * picked. Every control states what it is - a label, not an eyebrow - and
 * the numbers (the rating thresholds, the counts) stay in mono.
 */

export type AgentSort = 'rating' | 'reviews' | 'listings';

export interface AgentFilterState {
  /** The city, or null for "any". */
  city: string | null;
  /** The specialty, or null for "any". */
  specialty: string | null;
  /** The lowest rating, or null for "any". */
  minRating: number | null;
  /** The sort order. */
  sort: AgentSort;
}

export const EMPTY_AGENT_FILTERS: AgentFilterState = {
  city: null,
  specialty: null,
  minRating: null,
  sort: 'rating',
};

const RATING_OPTIONS: Array<{ value: number | null; label: string }> = [
  { value: null, label: 'any' },
  { value: 4, label: '4' },
  { value: 4.5, label: '4.5' },
  { value: 4.8, label: '4.8' },
];

const SORT_OPTIONS: AgentSort[] = ['rating', 'reviews', 'listings'];

export interface AgentFiltersProps {
  /** The cities the catalogue knows about. */
  cities: string[];
  /** The specialties the catalogue knows about. */
  specialties: string[];
  /** The current state. */
  value: AgentFilterState;
  /** Called with the next state. */
  onChange: (next: AgentFilterState) => void;
  /** Called when the reader clears the filters. */
  onClear: () => void;
  className?: string;
}

export function AgentFilters({
  cities,
  specialties,
  value,
  onChange,
  onClear,
  className,
}: AgentFiltersProps) {
  const t = useTranslations('agents');

  const pickCity = (city: string | null) => onChange({ ...value, city });
  const pickSpecialty = (specialty: string | null) => onChange({ ...value, specialty });
  const pickRating = (rating: number | null) => onChange({ ...value, minRating: rating });
  const pickSort = (sort: AgentSort) => onChange({ ...value, sort });

  const pill = (active: boolean) =>
    [
      'rounded-full border px-[10px] py-1 text-[12px] transition-colors',
      active
        ? 'border-foreground bg-foreground text-background'
        : 'border-border bg-transparent text-foreground hover:bg-muted',
    ].join(' ');

  return (
    <div className={['flex flex-col gap-4', className].filter(Boolean).join(' ')}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[14px] font-semibold text-foreground">{t('filters.title')}</span>
        <button
          type="button"
          onClick={onClear}
          className="p-0 text-[12px] font-normal text-muted-foreground hover:text-foreground"
        >
          {t('filters.clear')}
        </button>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-[12px] font-medium text-foreground">{t('filters.city')}</span>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label={t('filters.city')}>
          <button
            type="button"
            className={pill(value.city === null)}
            aria-pressed={value.city === null}
            onClick={() => pickCity(null)}
          >
            {t('filters.any')}
          </button>
          {cities.map((city) => (
            <button
              key={city}
              type="button"
              className={pill(value.city === city)}
              aria-pressed={value.city === city}
              onClick={() => pickCity(value.city === city ? null : city)}
            >
              {city}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-[12px] font-medium text-foreground">
          {t('filters.specialty')}
        </span>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label={t('filters.specialty')}>
          <button
            type="button"
            className={pill(value.specialty === null)}
            aria-pressed={value.specialty === null}
            onClick={() => pickSpecialty(null)}
          >
            {t('filters.any')}
          </button>
          {specialties.map((specialty) => (
            <button
              key={specialty}
              type="button"
              className={pill(value.specialty === specialty)}
              aria-pressed={value.specialty === specialty}
              onClick={() => pickSpecialty(value.specialty === specialty ? null : specialty)}
            >
              {specialty}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-[12px] font-medium text-foreground">
          {t('filters.minRating')}
        </span>
        <div
          className="grid grid-cols-4 overflow-hidden rounded-md border border-border"
          role="group"
          aria-label={t('filters.minRating')}
        >
          {RATING_OPTIONS.map((option, index) => {
            const active = value.minRating === option.value;
            return (
              <button
                key={option.label}
                type="button"
                onClick={() => pickRating(option.value)}
                aria-pressed={active}
                className={[
                  'h-8 border-border text-[12px] font-medium',
                  index < RATING_OPTIONS.length - 1 ? 'border-r' : '',
                  active
                    ? 'bg-foreground text-background'
                    : 'bg-transparent text-foreground hover:bg-muted',
                ].join(' ')}
              >
                {option.value === null
                  ? t('filters.any')
                  : t('filters.stars', { count: option.value })}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-[12px] font-medium text-foreground">{t('filters.sortBy')}</span>
        <div
          className="flex flex-col overflow-hidden rounded-md border border-border"
          role="group"
          aria-label={t('filters.sortBy')}
        >
          {SORT_OPTIONS.map((option, index) => {
            const active = value.sort === option;
            return (
              <button
                key={option}
                type="button"
                onClick={() => pickSort(option)}
                aria-pressed={active}
                className={[
                  'h-8 border-border px-2.5 text-left text-[13px]',
                  index < SORT_OPTIONS.length - 1 ? 'border-b' : '',
                  active ? 'bg-muted font-medium text-foreground' : 'text-foreground hover:bg-muted',
                ].join(' ')}
              >
                {t(`sort.${option}`)}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
