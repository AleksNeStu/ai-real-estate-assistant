'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Search, SlidersHorizontal, RefreshCw, Users, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/ui/page-header';

import { getAgents } from '@/lib/api';
import type { AgentProfile, AgentFilters } from '@/lib/types';
import { AgentCard } from '@/components/agents/agent-card';
import { EmptyState } from '@/components/ui/states';

const SORT_OPTIONS = [
  { value: 'rating', label: 'Rating (High to Low)' },
  { value: 'reviews', label: 'Most Reviews' },
  { value: 'listings', label: 'Most Listings' },
  { value: 'created', label: 'Newest First' },
] as const;

type SortOption = (typeof SORT_OPTIONS)[number]['value'];

export default function AgentsPage({ params }: { params: Promise<{ locale: string }> }) {
  const t = useTranslations();
  const tPage = useTranslations('pages.agents');

  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [locale, setLocale] = useState<string>('en');
  const pageSize = 12;

  const [filters, setFilters] = useState<AgentFilters>({
    sort_by: 'rating',
    sort_order: 'desc',
  });

  // Local filter state for the form
  const [localCity, setLocalCity] = useState('');
  const [localSpecialty, setLocalSpecialty] = useState('');
  const [localMinRating, setLocalMinRating] = useState('any');
  const [localSortBy, setLocalSortBy] = useState<SortOption>('rating');

  // Get locale from params
  useEffect(() => {
    params.then((p) => setLocale(p.locale));
  }, [params]);

  const loadAgents = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await getAgents({
        ...filters,
        page,
        page_size: pageSize,
      });

      setAgents(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents');
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  const applyFilters = () => {
    setFilters({
      city: localCity || undefined,
      specialty: localSpecialty || undefined,
      min_rating:
        localMinRating && localMinRating !== 'any' ? parseFloat(localMinRating) : undefined,
      sort_by: localSortBy,
      sort_order: 'desc',
    });
    setPage(1);
  };

  const clearFilters = () => {
    setLocalCity('');
    setLocalSpecialty('');
    setLocalMinRating('any');
    setLocalSortBy('rating');
    setFilters({
      sort_by: 'rating',
      sort_order: 'desc',
    });
    setPage(1);
  };

  const hasActiveFilters = filters.city || filters.specialty || filters.min_rating;

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <PageHeader
        className="mb-8"
        title={tPage('title')}
        description={tPage('description')}
      />

      {/* Search and Filter Bar */}
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex flex-1 flex-col gap-4 sm:flex-row">
          {/* Quick Search */}
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by city..."
              value={localCity}
              onChange={(e) => setLocalCity(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Quick Sort */}
          <Select
            value={localSortBy}
            onValueChange={(value: SortOption) => {
              setLocalSortBy(value);
              setFilters((prev) => ({ ...prev, sort_by: value }));
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Filter Button */}
        <div className="flex gap-2">
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <X className="mr-2 h-4 w-4" />
              Clear Filters
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={applyFilters}>
            <SlidersHorizontal className="mr-2 h-4 w-4" />
            Apply Filters
          </Button>
          <Button variant="ghost" size="icon" onClick={loadAgents}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Advanced Filters */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label>{t('agents.filters.city')}</Label>
              <Input
                placeholder="Enter city..."
                value={localCity}
                onChange={(e) => setLocalCity(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>{t('agents.filters.specialty')}</Label>
              <Input
                placeholder="e.g., Residential, Commercial..."
                value={localSpecialty}
                onChange={(e) => setLocalSpecialty(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>{t('agents.filters.minRating')}</Label>
              <Select value={localMinRating} onValueChange={(value) => setLocalMinRating(value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Any rating" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">Any</SelectItem>
                  <SelectItem value="4">4+ Stars</SelectItem>
                  <SelectItem value="4.5">4.5+ Stars</SelectItem>
                  <SelectItem value="4.8">4.8+ Stars</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{t('agents.filters.sortBy')}</Label>
              <Select
                value={localSortBy}
                onValueChange={(value: SortOption) => setLocalSortBy(value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  {SORT_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {error && (
        <Card className="mb-6 border-destructive">
          <CardContent className="flex items-center gap-2 p-4 text-destructive">
            <span>{error}</span>
            <Button variant="ghost" size="sm" onClick={loadAgents}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="flex gap-4">
                  <Skeleton className="h-20 w-20 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                    <Skeleton className="h-3 w-2/3" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : agents.length === 0 ? (
        <EmptyState
          icon={Users}
          title={t('agents.noAgents')}
          description={t('agents.noAgentsDescription')}
          action={
            hasActiveFilters ? (
              <Button variant="outline" onClick={clearFilters}>
                {t('agents.filters.clear')}
              </Button>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="mb-4 text-sm text-muted-foreground">
            {total} {total === 1 ? 'agent' : 'agents'} found
          </div>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent) => (
              <AgentCard key={agent.id} agent={agent} locale={locale} />
            ))}
          </div>
        </>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-8 flex justify-center gap-2">
          <Button variant="outline" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <span className="flex items-center px-4 text-sm">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
