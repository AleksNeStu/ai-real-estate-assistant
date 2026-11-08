'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  AlertCircle,
  ArrowRight,
  Building2,
  DollarSign,
  BarChart3,
} from 'lucide-react';
import { compareAreas, ApiError } from '@/lib/api';
import { AreaComparison } from '@/lib/types';
import { useTranslations } from 'next-intl';

/**
 * Maps the API amenity_availability keys to the catalogue keys that carry their
 * reader-visible label. Unknown keys fall back to the raw key.
 */
const AMENITY_LABEL_KEYS: Record<string, string> = {
  parking: 'parking',
  garden: 'garden',
  pool: 'pool',
  furnished: 'furnished',
  balcony: 'balcony',
  elevator: 'elevator',
};

interface MetricRowProps {
  label: string;
  value1: number | string | undefined;
  value2: number | string | undefined;
  unit?: string;
  format?: 'number' | 'currency' | 'percent';
  higherIsBetter?: boolean;
}

function MetricRow({
  label,
  value1,
  value2,
  unit = '',
  format = 'number',
  higherIsBetter = true,
}: MetricRowProps) {
  const formatValue = (val: number | string | undefined): string => {
    if (val === undefined || val === null) return 'N/A';
    if (typeof val === 'string') return val;
    if (format === 'currency') return `$${val.toLocaleString()}`;
    if (format === 'percent') return `${val.toFixed(1)}%`;
    return `${val.toLocaleString()}${unit}`;
  };

  const num1 = typeof value1 === 'number' ? value1 : 0;
  const num2 = typeof value2 === 'number' ? value2 : 0;
  const diff = num1 - num2;
  const diffPercent = num2 !== 0 ? ((diff / num2) * 100).toFixed(1) : '0';

  const isPositive = diff > 0;
  const isBetter = higherIsBetter ? isPositive : !isPositive;

  return (
    <div className="grid grid-cols-5 items-center py-3 border-b border-border/50 gap-4">
      <div className="col-span-2 text-right">
        <span className="font-semibold">{formatValue(value1)}</span>
      </div>
      <div className="col-span-1 text-center">
        <div className="text-xs text-muted-foreground">{label}</div>
        {diff !== 0 && (
          <div
            className={`flex items-center justify-center gap-1 text-xs ${isBetter ? 'text-success' : 'text-destructive'}`}
          >
            {isPositive ? (
              <TrendingUp className="h-3 w-3" aria-hidden="true" />
            ) : (
              <TrendingDown className="h-3 w-3" aria-hidden="true" />
            )}
            <span>{diffPercent}%</span>
          </div>
        )}
      </div>
      <div className="col-span-2 text-left">
        <span className="font-semibold">{formatValue(value2)}</span>
      </div>
    </div>
  );
}

export function AreaComparisonComponent() {
  const t = useTranslations('marketTrends');
  const tInv = useTranslations('investment');
  const tCompare = useTranslations('pages.tools.compare');
  const [city1, setCity1] = useState('Warsaw');
  const [city2, setCity2] = useState('Krakow');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<AreaComparison | null>(null);

  const handleCompare = async () => {
    if (!city1.trim() || !city2.trim()) {
      setError(t('areaComparison.bothCitiesRequired'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await compareAreas(city1.trim(), city2.trim());
      setComparison(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t('areaComparison.compareFailed'));
      }
    } finally {
      setLoading(false);
    }
  };

  const TrendIcon =
    comparison && comparison.price_difference > 0
      ? TrendingUp
      : comparison && comparison.price_difference < 0
        ? TrendingDown
        : Minus;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" aria-hidden="true" />
          {tInv('areaComparison.title')}
        </CardTitle>
        <CardDescription>{t('areaComparison.description')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Input Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="city1">{t('areaComparison.firstCity')}</Label>
            <Input
              id="city1"
              placeholder={t('areaComparison.cityPlaceholder')}
              value={city1}
              onChange={(e) => setCity1(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCompare()}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="city2">{t('areaComparison.secondCity')}</Label>
            <Input
              id="city2"
              placeholder={t('areaComparison.cityPlaceholder')}
              value={city2}
              onChange={(e) => setCity2(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCompare()}
            />
          </div>
          <div className="flex items-end">
            <Button onClick={handleCompare} disabled={loading} className="w-full">
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
              {tCompare('compare')}
            </Button>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div
            className="flex items-center gap-2 p-4 border border-destructive/20 bg-destructive/10 rounded-lg"
            role="alert"
          >
            <AlertCircle className="h-5 w-5 text-destructive" aria-hidden="true" />
            <p className="text-destructive">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && !comparison && (
          <div className="flex items-center justify-center h-48" role="status" aria-live="polite">
            <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
          </div>
        )}

        {/* Comparison Results */}
        {comparison && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="bg-muted/50">
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2">
                    <TrendIcon className="h-5 w-5 text-primary" aria-hidden="true" />
                    <div>
                      <p className="text-sm text-muted-foreground">{t('areaComparison.priceDifference')}</p>
                      <p className="text-lg font-semibold">
                        {comparison.price_difference > 0 ? '+' : ''}
                        {comparison.price_difference_percent.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-muted/50">
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-5 w-5 text-success" aria-hidden="true" />
                    <div>
                      <p className="text-sm text-muted-foreground">{t('areaComparison.cheaperArea')}</p>
                      <p className="text-lg font-semibold">{comparison.cheaper_area}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-muted/50">
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2">
                    <Building2 className="h-5 w-5 text-info" aria-hidden="true" />
                    <div>
                      <p className="text-sm text-muted-foreground">{t('areaComparison.moreListings')}</p>
                      <p className="text-lg font-semibold">{comparison.more_properties_area}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Comparison Table */}
            <div className="rounded-lg border">
              {/* Header */}
              <div className="grid grid-cols-5 bg-muted/50 p-3 font-semibold text-sm">
                <div className="col-span-2 text-center">{comparison.area1.city}</div>
                <div className="col-span-1 text-center">{t('areaComparison.metric')}</div>
                <div className="col-span-2 text-center">{comparison.area2.city}</div>
              </div>

              {/* Metrics */}
              <div className="p-3">
                <MetricRow
                  label={t('areaComparison.avgPrice')}
                  value1={comparison.area1.avg_price}
                  value2={comparison.area2.avg_price}
                  format="currency"
                  higherIsBetter={false}
                />
                <MetricRow
                  label={t('areaComparison.medianPrice')}
                  value1={comparison.area1.median_price}
                  value2={comparison.area2.median_price}
                  format="currency"
                  higherIsBetter={false}
                />
                <MetricRow
                  label={t('areaComparison.pricePerSqm')}
                  value1={comparison.area1.avg_price_per_sqm}
                  value2={comparison.area2.avg_price_per_sqm}
                  format="currency"
                  higherIsBetter={false}
                />
                <MetricRow
                  label={t('areaComparison.listings')}
                  value1={comparison.area1.property_count}
                  value2={comparison.area2.property_count}
                  format="number"
                  higherIsBetter={true}
                />
                <MetricRow
                  label={t('areaComparison.avgRooms')}
                  value1={comparison.area1.most_common_room_count}
                  value2={comparison.area2.most_common_room_count}
                  format="number"
                  higherIsBetter={false}
                />
              </div>
            </div>

            {/* Amenity Comparison */}
            {comparison.area1.amenity_availability &&
              Object.keys(comparison.area1.amenity_availability).length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold mb-3">{t('areaComparison.amenityAvailability')}</h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {Object.entries(comparison.area1.amenity_availability).map(([key, val1]) => {
                      const val2 = comparison.area2.amenity_availability?.[key] ?? 0;
                      const diff = val1 - val2;
                      const amenityKey = AMENITY_LABEL_KEYS[key];
                      const amenityLabel = amenityKey
                        ? tInv(`areaComparison.amenities.${amenityKey}`)
                        : key.replace(/_/g, ' ');
                      return (
                        <div key={key} className="text-sm p-2 bg-muted/30 rounded">
                          <div className="capitalize font-medium">{amenityLabel}</div>
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <span>{val1.toFixed(0)}%</span>
                            <ArrowRight className="h-3 w-3" aria-hidden="true" />
                            <span>{val2.toFixed(0)}%</span>
                            {diff !== 0 && (
                              <span className={diff > 0 ? 'text-success' : 'text-destructive'}>
                                ({diff > 0 ? '+' : ''}
                                {diff.toFixed(0)}%)
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
