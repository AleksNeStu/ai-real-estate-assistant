'use client';

import { useState, useEffect, useCallback } from 'react';
import { format } from 'date-fns';
import { useTranslations } from 'next-intl';
import {
  Search,
  Eye,
  MousePointerClick,
  Wrench,
  Download,
  Star,
  TrendingUp,
  BarChart3,
  Calendar,
  Clock,
  MapPin,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/ui/page-header';
import { ErrorState } from '@/components/ui/states';

import { getUserActivitySummary, getUserActivityTrends, exportUserActivityCSV } from '@/lib/api';
import type { UserActivitySummary, UserActivityTrendPoint } from '@/lib/types';

// Recharts components for charts
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// Chart colors
const CHART_COLORS = [
  'hsl(var(--chart-1))', // blue
  'hsl(var(--chart-2))', // green
  'hsl(var(--chart-3))', // amber
  'hsl(var(--chart-4))', // purple
  'hsl(var(--chart-6))', // pink
  'hsl(var(--chart-5))', // cyan
  'hsl(var(--caution))', // orange
  'hsl(var(--chart-7))', // lime
];

// Format milliseconds to human-readable time
function formatDuration(ms?: number): string {
  if (!ms) return 'N/A';
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

// Format date for display
function formatDate(dateStr: string): string {
  try {
    return format(new Date(dateStr), 'MMM d, yyyy');
  } catch {
    return dateStr;
  }
}

// Metric Card Component
function MetricCard({
  title,
  value,
  icon: Icon,
  description,
  color = 'blue',
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  description?: string;
  color?: 'blue' | 'green' | 'purple' | 'amber' | 'pink';
}) {
  const colorClasses = {
    blue: 'text-info bg-info/15',
    green: 'text-success bg-success/15',
    purple: 'text-critical bg-critical/20',
    amber: 'text-warning bg-warning/15',
    pink: 'text-chart-6 bg-chart-6/20',
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </CardContent>
    </Card>
  );
}

export default function UsagePage() {
  const t = useTranslations('pages.usage');
  const tCommon = useTranslations('common');
  const [summary, setSummary] = useState<UserActivitySummary | null>(null);
  const [trends, setTrends] = useState<UserActivityTrendPoint[]>([]);
  const [interval, setInterval] = useState<'day' | 'week' | 'month'>('week');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  // Load data
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [summaryData, trendsData] = await Promise.all([
        getUserActivitySummary(),
        getUserActivityTrends({ interval, periods: 12 }),
      ]);

      setSummary(summaryData);
      setTrends(trendsData.trends);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [interval, t]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle export
  const handleExport = async () => {
    try {
      setExporting(true);
      const blob = await exportUserActivityCSV();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `usage-${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export:', err);
    } finally {
      setExporting(false);
    }
  };

  // Prepare chart data
  const topToolsData =
    summary?.top_tools?.slice(0, 6).map((tool) => ({
      name: tool.tool_name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
      count: tool.count,
    })) || [];

  const topCitiesData =
    summary?.top_search_cities?.slice(0, 8).map((city) => ({
      name: city.city,
      count: city.count,
    })) || [];

  const dailyEventsData =
    summary?.event_counts_by_day?.map((day) => ({
      date: format(new Date(day.date), 'MMM dd'),
      count: day.count,
    })) || [];

  const trendsChartData = trends.map((trend) => ({
    date: format(new Date(trend.date), 'MMM dd'),
    searches: trend.searches,
    propertyViews: trend.property_views,
    toolUses: trend.tool_uses,
    exports: trend.exports,
  }));

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <ErrorState
          title={tCommon('error')}
          description={error}
          onRetry={loadData}
          retryLabel={tCommon('retry')}
        />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <PageHeader
        title={t('title')}
        description={t('description')}
        actions={
          <div className="flex gap-2">
            <Select
              value={interval}
              onValueChange={(v: 'day' | 'week' | 'month') => setInterval(v)}
            >
              <SelectTrigger className="w-[140px]">
                <Calendar className="mr-2 h-4 w-4" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="day">{t('interval.day')}</SelectItem>
                <SelectItem value="week">{t('interval.week')}</SelectItem>
                <SelectItem value="month">{t('interval.month')}</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={loadData} disabled={loading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              {t('actions.refresh')}
            </Button>
            <Button variant="outline" onClick={handleExport} disabled={exporting}>
              <Download className="mr-2 h-4 w-4" />
              {exporting ? tCommon('exporting') : t('actions.exportCsv')}
            </Button>
          </div>
        }
      />

      {/* Summary Period Badge */}
      {summary && (
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-sm">
            <Calendar className="mr-1 h-3 w-3" />
            {formatDate(summary.period_start)} - {formatDate(summary.period_end)}
          </Badge>
          <span className="text-sm text-muted-foreground">
            {t('sessions', { count: summary.unique_sessions })}
          </span>
        </div>
      )}

      {/* Summary Cards */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-8 w-8 rounded-lg" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-20" />
                <Skeleton className="h-3 w-32 mt-2" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : summary ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title={t('totalSearches')}
            value={summary.total_searches.toLocaleString()}
            icon={Search}
            color="blue"
          />
          <MetricCard
            title={t('propertyViews')}
            value={summary.total_property_views.toLocaleString()}
            icon={Eye}
            description={t('propertiesViewed')}
            color="green"
          />
          <MetricCard
            title={t('toolsUsed')}
            value={summary.total_tool_uses.toLocaleString()}
            icon={Wrench}
            description={t('calculatorTools')}
            color="purple"
          />
          <MetricCard
            title={t('avgResponseTime')}
            value={formatDuration(summary.avg_processing_time_ms)}
            icon={Clock}
            description={t('processingTime')}
            color="amber"
          />
        </div>
      ) : null}

      {/* Additional Metrics Row */}
      {summary && !loading && (
        <div className="grid gap-4 md:grid-cols-3">
          <MetricCard
            title={t('propertyClicks')}
            value={summary.total_property_clicks.toLocaleString()}
            icon={MousePointerClick}
            description={t('clickThroughRate')}
            color="pink"
          />
          <MetricCard
            title={t('exports')}
            value={summary.total_exports.toLocaleString()}
            icon={Download}
            description={t('dataExported')}
            color="blue"
          />
          <MetricCard
            title={t('favorites')}
            value={summary.total_favorites.toLocaleString()}
            icon={Star}
            description={t('propertiesSaved')}
            color="amber"
          />
        </div>
      )}

      {/* Charts Section */}
      <Tabs defaultValue="trends" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trends">
            <TrendingUp className="mr-2 h-4 w-4" />
            {t('tabs.activityTrends')}
          </TabsTrigger>
          <TabsTrigger value="tools">
            <Wrench className="mr-2 h-4 w-4" />
            {t('tabs.topTools')}
          </TabsTrigger>
          <TabsTrigger value="cities">
            <MapPin className="mr-2 h-4 w-4" />
            {t('tabs.topCities')}
          </TabsTrigger>
          <TabsTrigger value="daily">
            <BarChart3 className="mr-2 h-4 w-4" />
            {t('tabs.dailyActivity')}
          </TabsTrigger>
        </TabsList>

        {/* Trends Tab */}
        <TabsContent value="trends" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('charts.activityOverTime')}</CardTitle>
              <CardDescription>
                {t('charts.activityOverTimeDescription', { interval: t(`interval.${interval}`) })}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-72 w-full" />
              ) : trendsChartData.length > 0 ? (
                <div role="img" aria-label={t('aria.activityOverTime')}>
                  <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={trendsChartData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => value.toLocaleString()}
                    />
                    <Tooltip
                      formatter={(value: number) => value.toLocaleString()}
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                      }}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="searches"
                      name={t('series.searches')}
                      stroke={CHART_COLORS[0]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="propertyViews"
                      name={t('series.propertyViews')}
                      stroke={CHART_COLORS[1]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="toolUses"
                      name={t('series.toolUses')}
                      stroke={CHART_COLORS[2]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="exports"
                      name={t('series.exports')}
                      stroke={CHART_COLORS[3]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex items-center justify-center h-72 text-muted-foreground">
                  {t('empty.noTrendData')}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tools Tab */}
        <TabsContent value="tools" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('charts.mostUsedTools')}</CardTitle>
              <CardDescription>{t('charts.mostUsedToolsDescription')}</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-72 w-full" />
              ) : topToolsData.length > 0 ? (
                <div role="img" aria-label={t('aria.mostUsedTools')}>
                  <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={topToolsData} layout="horizontal">
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => value.toLocaleString()}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      width={100}
                    />
                    <Tooltip
                      formatter={(value: number) => value.toLocaleString()}
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                      }}
                    />
                    <Bar dataKey="count" fill={CHART_COLORS[0]} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-72 text-muted-foreground">
                  <Wrench className="h-12 w-12 mb-4" />
                  <p>{t('empty.noToolUsage')}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Cities Tab */}
        <TabsContent value="cities" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>{t('charts.topSearchCities')}</CardTitle>
                <CardDescription>{t('charts.topSearchCitiesDescription')}</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-72 w-full" />
                ) : topCitiesData.length > 0 ? (
                  <div role="img" aria-label={t('aria.topSearchCities')}>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={topCitiesData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis
                        dataKey="name"
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        angle={-45}
                        textAnchor="end"
                        height={60}
                      />
                      <YAxis
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(value) => value.toLocaleString()}
                      />
                      <Tooltip
                        formatter={(value: number) => value.toLocaleString()}
                        contentStyle={{
                          backgroundColor: 'hsl(var(--background))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                        }}
                      />
                      <Bar dataKey="count" fill={CHART_COLORS[1]} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-72 text-muted-foreground">
                    <MapPin className="h-12 w-12 mb-4" />
                    <p>{t('empty.noCityData')}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* City Distribution Pie Chart */}
            {topCitiesData.length > 0 && !loading && (
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle>{t('charts.searchDistribution')}</CardTitle>
                  <CardDescription>{t('charts.searchDistributionDescription')}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div role="img" aria-label={t('aria.searchDistribution')}>
                    <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={topCitiesData}
                        dataKey="count"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={(entry) =>
                          `${entry.name}: ${Math.round((entry.count / topCitiesData.reduce((sum, d) => sum + d.count, 0)) * 100)}%`
                        }
                        labelLine={false}
                      >
                        {topCitiesData.map((_, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={CHART_COLORS[index % CHART_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(value: number) => value.toLocaleString()}
                        contentStyle={{
                          backgroundColor: 'hsl(var(--background))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                        }}
                      />
                    </PieChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Daily Activity Tab */}
        <TabsContent value="daily" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('charts.dailyActivity')}</CardTitle>
              <CardDescription>{t('charts.dailyActivityDescription')}</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-72 w-full" />
              ) : dailyEventsData.length > 0 ? (
                <div role="img" aria-label={t('aria.dailyActivity')}>
                  <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={dailyEventsData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => value.toLocaleString()}
                    />
                    <Tooltip
                      formatter={(value: number) => value.toLocaleString()}
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                      }}
                    />
                    <Bar dataKey="count" fill={CHART_COLORS[5]} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-72 text-muted-foreground">
                  <BarChart3 className="h-12 w-12 mb-4" />
                  <p>{t('empty.noDailyActivity')}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
