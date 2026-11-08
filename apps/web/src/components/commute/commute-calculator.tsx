'use client';

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import {
  MapPin,
  Clock,
  Car,
  Bike,
  Footprints,
  Train,
  Plus,
  Trash2,
  MapPinned,
  Save,
  X,
  Star,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { CommuteBadge } from './commute-badge';
import { calculateCommuteTime } from '@/lib/api';
import type {
  CommuteMode,
  CommuteTimeRequest,
  CommuteTimeResult,
  SavedDestination,
} from '@/lib/types';

// Icons for transport modes
const MODE_ICONS: Record<CommuteMode, React.ReactNode> = {
  driving: <Car className="h-4 w-4" />,
  walking: <Footprints className="h-4 w-4" />,
  bicycling: <Bike className="h-4 w-4" />,
  transit: <Train className="h-4 w-4" />,
};

const MODE_LABEL_KEYS: Record<CommuteMode, string> = {
  driving: 'driving',
  walking: 'walking',
  bicycling: 'bicycling',
  transit: 'transit',
};

export interface SavedDestinationWithResult extends SavedDestination {
  lastCalculated?: CommuteTimeResult;
}

export interface CommuteCalculatorProps {
  propertyId: string;
  propertyLat?: number;
  propertyLon?: number;
  onCommuteCalculated?: (result: CommuteTimeResult) => void;
  showDestinationForm?: boolean;
  className?: string;
  compact?: boolean;
}

export function CommuteCalculator({
  propertyId,
  propertyLat,
  propertyLon,
  onCommuteCalculated,
  showDestinationForm: initialShowForm = false,
  className,
  compact = false,
}: CommuteCalculatorProps) {
  const [destinations, setDestinations] = useState<SavedDestinationWithResult[]>([]);
  const [isAdding, setIsAdding] = useState(initialShowForm);
  const [selectedMode, setSelectedMode] = useState<CommuteMode>('transit');
  const t = useTranslations('pages.commute');
  const tCommon = useTranslations('common');
  const tExtra = useTranslations('pages.commuteExtra');
  const [error, setError] = useState<string | null>(null);
  const [calculatingId, setCalculatingId] = useState<string | null>(null);

  // Form state for adding new destination
  const [form, setForm] = useState({
    name: '',
    address: '',
    lat: '',
    lon: '',
  });

  // Load saved destinations from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('commute-destinations');
    if (saved) {
      try {
        const parsed: SavedDestination[] = JSON.parse(saved);
        setDestinations(parsed.map((d) => ({ ...d, lastCalculated: undefined })));
      } catch {
        // Invalid data, ignore
      }
    }
  }, []);

  // Save destinations to localStorage when they change
  const saveToStorage = useCallback((dests: SavedDestination[]) => {
    const toSave = dests.map(({ id, name, address, latitude, longitude, is_default }) => ({
      id,
      name,
      address,
      latitude,
      longitude,
      is_default,
    }));
    localStorage.setItem('commute-destinations', JSON.stringify(toSave));
  }, []);

  // Handle calculating commute for a specific destination
  const handleCalculate = useCallback(
    async (destination: SavedDestinationWithResult) => {
      if (!propertyLat || !propertyLon) {
        setError(t('errors.propertyLocation'));
        return;
      }

      setCalculatingId(destination.id);
      setError(null);

      try {
        const request: CommuteTimeRequest = {
          property_id: propertyId,
          destination_lat: destination.latitude,
          destination_lon: destination.longitude,
          mode: selectedMode,
          destination_name: destination.name,
        };

        const response = await calculateCommuteTime(request);

        // Update the destination with the result
        setDestinations((prev) =>
          prev.map((d) => (d.id === destination.id ? { ...d, lastCalculated: response.result } : d))
        );

        if (onCommuteCalculated && response.result) {
          onCommuteCalculated(response.result);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : t('errors.calculate'));
      } finally {
        setCalculatingId(null);
      }
    },
    [propertyId, propertyLat, propertyLon, selectedMode, onCommuteCalculated, t]
  );

  // Add a new destination
  const handleAddDestination = useCallback(() => {
    const lat = parseFloat(form.lat);
    const lon = parseFloat(form.lon);

    if (!form.name || isNaN(lat) || isNaN(lon)) {
      setError(t('errors.requiredFields'));
      return;
    }

    const newDestination: SavedDestinationWithResult = {
      id: `dest-${Date.now()}`,
      name: form.name,
      address: form.address || undefined,
      latitude: lat,
      longitude: lon,
      is_default: false,
    };

    const newDestinations = [...destinations, newDestination];
    setDestinations(newDestinations);
    saveToStorage(newDestinations);
    setForm({ name: '', address: '', lat: '', lon: '' });
    setIsAdding(false);
  }, [destinations, form, saveToStorage, t]);

  // Remove a destination
  const handleRemove = useCallback(
    (id: string) => {
      const filtered = destinations.filter((d) => d.id !== id);
      setDestinations(filtered.map((d) => ({ ...d, lastCalculated: undefined })));
      saveToStorage(filtered);
    },
    [destinations, saveToStorage]
  );

  // Set a destination as default
  const handleSetDefault = useCallback(
    (id: string) => {
      const updated = destinations.map((d) => ({
        ...d,
        is_default: d.id === id,
      }));
      setDestinations(updated);
      saveToStorage(updated);
    },
    [destinations, saveToStorage]
  );

  // Check if we can calculate
  const canCalculate = useMemo(() => {
    return propertyLat !== undefined && propertyLon !== undefined;
  }, [propertyLat, propertyLon]);

  return (
    <div className={cn('w-full', className)}>
      {/* Header with Mode Selector */}
      <div className={cn('flex items-center justify-between mb-4', compact && 'flex-wrap')}>
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{t('title')}</span>
        </div>
        <Select
          value={selectedMode}
          onValueChange={(value) => setSelectedMode(value as CommuteMode)}
        >
          <SelectTrigger className="w-32">
            <SelectValue placeholder={t('modePlaceholder')} />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(MODE_LABEL_KEYS).map(([mode, labelKey]) => (
              <SelectItem key={mode} value={mode}>
                <div className="flex items-center gap-2">
                  {MODE_ICONS[mode as CommuteMode]}
                  <span>{t(`modes.${labelKey}`)}</span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Error display */}
      {error && (
        <div
          className="p-3 rounded-md bg-destructive/10 text-sm text-destructive bg-destructive/15/20 dark:text-destructive mb-4"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* Destination list */}
      {destinations.length > 0 ? (
        <div className="space-y-3">
          {destinations.map((dest) => (
            <div
              key={dest.id}
              className={cn(
                'p-3 border rounded-lg',
                dest.is_default && 'border-primary bg-primary/5 dark:bg-primary/10'
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <div>
                    <div className="font-medium">{dest.name}</div>
                    {dest.address && (
                      <div className="text-sm text-muted-foreground">{dest.address}</div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {dest.lastCalculated && (
                    <CommuteBadge
                      duration={dest.lastCalculated.duration_seconds}
                      mode={selectedMode}
                      showIcon={false}
                    />
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleCalculate(dest)}
                    disabled={!canCalculate || calculatingId === dest.id}
                    aria-label={t('calculateAria')}
                  >
                    {calculatingId === dest.id ? (
                      <div className="h-4 w-4 animate-spin border-2 border-current border-t-transparent rounded-full" />
                    ) : (
                      <Clock className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSetDefault(dest.id)}
                    aria-label={t('setDefaultAria')}
                  >
                    <Star
                      className={cn(
                        'h-4 w-4',
                        dest.is_default ? 'fill-warning text-warning' : 'text-muted-foreground'
                      )}
                    />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemove(dest.id)}
                    aria-label={t('removeDestinationAria')}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </div>

              {dest.lastCalculated && (
                <div className="mt-2 pt-2 border-t border-dashed text-xs text-muted-foreground">
                  <div className="flex items-center gap-4">
                    <span>
                      {dest.lastCalculated.distance_text} {t('via')}{' '}
                      {t(`modes.${MODE_LABEL_KEYS[dest.lastCalculated.mode as CommuteMode]}`) ||
                        dest.lastCalculated.mode}
                    </span>
                    {dest.lastCalculated.arrival_time && (
                      <span>{t('arrival', { time: dest.lastCalculated.arrival_time })}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-6 text-sm text-muted-foreground">
          <MapPinned className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>{t('empty')}</p>
          <p className="text-xs">{tExtra('emptyHint')}</p>
        </div>
      )}

      {/* Add Destination Form */}
      {isAdding ? (
        <div className="mt-4 p-3 border rounded-lg bg-muted/50 dark:bg-muted/20">
          <div className="flex items-center justify-between mb-3">
            <span className="font-medium">{t('addDestination')}</span>
            <Button variant="ghost" size="sm" onClick={() => setIsAdding(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Label htmlFor="dest-name" className="text-sm">
                {t('nameLabel')} *
              </Label>
              <Input
                id="dest-name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder={t('namePlaceholder')}
                className="h-9"
              />
            </div>
            <div className="col-span-2">
              <Label htmlFor="dest-address" className="text-sm">
                {t('addressLabel')}
              </Label>
              <Input
                id="dest-address"
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
                placeholder={t('addressPlaceholder')}
                className="h-9"
              />
            </div>
            <div>
              <Label htmlFor="dest-lat" className="text-sm">
                {t('latitudeLabel')} *
              </Label>
              <Input
                id="dest-lat"
                type="number"
                step="any"
                value={form.lat}
                onChange={(e) => setForm({ ...form, lat: e.target.value })}
                placeholder={t('latPlaceholder')}
                className="h-9"
              />
            </div>
            <div>
              <Label htmlFor="dest-lon" className="text-sm">
                {t('longitudeLabel')} *
              </Label>
              <Input
                id="dest-lon"
                type="number"
                step="any"
                value={form.lon}
                onChange={(e) => setForm({ ...form, lon: e.target.value })}
                placeholder={t('lonPlaceholder')}
                className="h-9"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <Button
              size="sm"
              onClick={handleAddDestination}
              disabled={!form.name || !form.lat || !form.lon}
            >
              <Save className="h-4 w-4 mr-1" />
              {tCommon('save')}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setIsAdding(false)}>
              {tCommon('cancel')}
            </Button>
          </div>
        </div>
      ) : (
        <Button
          variant="outline"
          size="sm"
          className="mt-4 w-full"
          onClick={() => setIsAdding(true)}
        >
          <Plus className="h-4 w-4 mr-1" />
          {t('addDestination')}
        </Button>
      )}

      {/* Info about property coordinates */}
      {!canCalculate && (
        <div className="mt-4 text-xs text-muted-foreground flex items-center gap-1">
          <MapPin className="h-3 w-3" />
          {t('errors.propertyLocationHint')}
        </div>
      )}
    </div>
  );
}
