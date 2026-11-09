'use client';

import { StatTile } from '@/components/ui/stat-tile';
import { cn } from '@/lib/utils';
import type { UsageEventKind } from '@/components/usage/usage-format';

/**
 * The event-kind tiles.
 *
 * Five kinds of event, one tile each, and a tile is also the filter: the
 * kind that is chosen is the kind the ledger below speaks about. The chosen
 * one is marked with an ink rule under it - the same rule the ledger is
 * opened with, so the page has one line vocabulary.
 */

export interface UsageKindTileProps {
  kind: UsageEventKind;
  /** The total the API counted for this kind. */
  value: number;
  /** The label of the tile. */
  label: string;
  /** Whether this kind is the one the ledger speaks about. */
  selected: boolean;
  onSelect?: (kind: UsageEventKind) => void;
}

export function UsageKindTile({
  kind,
  value,
  label,
  selected,
  onSelect,
}: UsageKindTileProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect?.(kind)}
      aria-pressed={selected}
      data-testid={`usage-kind-${kind}`}
      className="flex flex-col gap-1 border-0 border-b-2 bg-transparent px-0 pb-2 pt-3 text-left transition-colors"
      style={{ borderBottomColor: selected ? 'hsl(var(--foreground))' : 'transparent' }}
    >
      <StatTile value={value} label={label} />
    </button>
  );
}

export interface UsageKindTilesProps {
  tiles: Array<{ kind: UsageEventKind; value: number; label: string }>;
  selected: UsageEventKind | null;
  onSelect?: (kind: UsageEventKind | null) => void;
  className?: string;
}

export function UsageKindTiles({ tiles, selected, onSelect, className }: UsageKindTilesProps) {
  return (
    <div className={cn('grid grid-cols-2 gap-x-6 gap-y-2 border-t border-foreground md:grid-cols-5', className)}>
      {tiles.map((tile) => (
        <UsageKindTile
          key={tile.kind}
          kind={tile.kind}
          value={tile.value}
          label={tile.label}
          selected={selected === tile.kind}
          onSelect={(kind) => onSelect?.(selected === kind ? null : kind)}
        />
      ))}
    </div>
  );
}
