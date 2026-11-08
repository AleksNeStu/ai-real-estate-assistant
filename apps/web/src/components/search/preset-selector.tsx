'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Filter, Plus, Trash2, Star, Loader2, ChevronDown } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  getFilterPresets,
  deleteFilterPreset,
  markFilterPresetUsed,
  setFilterPresetDefault,
  ApiError,
} from '@/lib/api';
import type { FilterPreset } from '@/lib/types';
import { SavePresetDialog } from './save-preset-dialog';

interface PresetSelectorProps {
  onPresetSelect: (preset: FilterPreset) => void;
  currentFilters: Record<string, unknown>;
  className?: string;
}

export function PresetSelector({ onPresetSelect, currentFilters, className }: PresetSelectorProps) {
  const [presets, setPresets] = useState<FilterPreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaveDialogOpen, setIsSaveDialogOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadPresets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getFilterPresets();
      setPresets(response.items);
    } catch (err) {
      if (err instanceof ApiError && err.category === 'auth') {
        setError('Log in to use presets');
      } else {
        setError('Failed to load presets');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPresets();
  }, [loadPresets]);

  const handleSelectPreset = async (preset: FilterPreset) => {
    try {
      // Mark as used (don't await to avoid blocking UI)
      markFilterPresetUsed(preset.id).catch(() => {});
      onPresetSelect(preset);
    } catch {
      // Still apply preset even if tracking fails
      onPresetSelect(preset);
    }
  };

  const handleDeletePreset = async (preset: FilterPreset, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Delete preset "${preset.name}"?`)) return;

    try {
      setDeletingId(preset.id);
      await deleteFilterPreset(preset.id);
      setPresets((prev) => prev.filter((p) => p.id !== preset.id));
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.message);
      }
    } finally {
      setDeletingId(null);
    }
  };

  const handleSetDefault = async (preset: FilterPreset, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await setFilterPresetDefault(preset.id);
      setPresets((prev) =>
        prev.map((p) => ({
          ...p,
          is_default: p.id === preset.id,
        }))
      );
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.message);
      }
    }
  };

  const handleSaveSuccess = (preset: FilterPreset) => {
    setPresets((prev) => {
      const filtered = prev.filter((p) => !preset.is_default || !p.is_default);
      return [preset, ...filtered];
    });
  };

  const hasFilters = Object.keys(currentFilters).some(
    (key) =>
      currentFilters[key] !== undefined &&
      currentFilters[key] !== '' &&
      currentFilters[key] !== null
  );

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className={className}>
            <Filter className="h-4 w-4 mr-2" aria-hidden="true" />
            Presets
            <ChevronDown className="h-4 w-4 ml-2" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          {loading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-4 w-4 animate-spin mr-2" aria-hidden="true" />
              Loading...
            </div>
          ) : error ? (
            <div className="px-2 py-4 text-center text-sm text-muted-foreground">{error}</div>
          ) : presets.length === 0 ? (
            <div className="px-2 py-4 text-center text-sm text-muted-foreground">
              No saved presets yet
            </div>
          ) : (
            presets.map((preset) => (
              <DropdownMenuItem
                key={preset.id}
                onClick={() => handleSelectPreset(preset)}
                className="flex items-center justify-between cursor-pointer"
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  {preset.is_default && (
                    <Star
                      className="h-3 w-3 text-warning fill-warning flex-shrink-0"
                      aria-hidden="true"
                    />
                  )}
                  <span className="truncate">{preset.name}</span>
                </div>
                <div className="flex items-center gap-1 ml-2">
                  {!preset.is_default && (
                    <button type="button"
                      onClick={(e) => handleSetDefault(preset, e)}
                      className="p-1 hover:bg-muted rounded"
                      title="Set as default"
                      aria-label={`Set ${preset.name} as default`}
                    >
                      <Star
                        className="h-3 w-3 text-muted-foreground hover:text-warning"
                        aria-hidden="true"
                      />
                    </button>
                  )}
                  <button type="button"
                    onClick={(e) => handleDeletePreset(preset, e)}
                    className="p-1 hover:bg-muted rounded"
                    disabled={deletingId === preset.id}
                    title="Delete preset"
                    aria-label={`Delete preset ${preset.name}`}
                  >
                    <Trash2
                      className="h-3 w-3 text-muted-foreground hover:text-destructive"
                      aria-hidden="true"
                    />
                  </button>
                </div>
              </DropdownMenuItem>
            ))
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => setIsSaveDialogOpen(true)}
            disabled={!hasFilters}
            className={!hasFilters ? 'opacity-50' : ''}
          >
            <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
            Save Current Filters
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <SavePresetDialog
        isOpen={isSaveDialogOpen}
        onOpenChange={setIsSaveDialogOpen}
        filters={currentFilters}
        onSuccess={handleSaveSuccess}
      />
    </>
  );
}
