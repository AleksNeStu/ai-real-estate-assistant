'use client';

import { useState, useEffect, useCallback } from 'react';
import { format } from 'date-fns';
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
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
  '#84cc16', // lime
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
    blue: 'text-blue-600 bg-blue-100',
    green: 'text-green-600 bg-green-100',
    purple: 'text-purple-600 bg-purple-100',
    amber: 'text-amber-600 bg-amber-100',
    pink: 'text-pink-600 bg-pink-100',
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
      setError(err instanceof Error ? err.message : 'Failed to load usage data');
    } finally {
      setLoading(false);
    }
  }, [interval]);

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
    Searches: trend.searches,
    'Property Views': trend.property_views,
    'Tool Uses': trend.tool_uses,
    Exports: trend.exports,
  }));

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertCircle className="h-12 w-12 text-destructive mb-4" />
        <p className="text-lg font-medium">{error}</p>
        <Button onClick={loadData} className="mt-4">
          <RefreshCw className="mr-2 h-4 w-4" />
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Usage Dashboard</h1>
          <p className="text-muted-foreground">Track your activity and analytics</p>
        </div>
        <div className="flex gap-2">
          <Select value={interval} onValueChange={(v: 'day' | 'week' | 'month') => setInterval(v)}>
            <SelectTrigger className="w-[140px]">
              <Calendar className="mr-2 h-4 w-4" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="day">Daily</SelectItem>
              <SelectItem value="week">Weekly</SelectItem>
              <SelectItem value="month">Monthly</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={loadData} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" onClick={handleExport} disabled={exporting}>
            <Download className="mr-2 h-4 w-4" />
            {exporting ? 'Exporting...' : 'Export CSV'}
          </Button>
        </div>
      </div>

      {/* Summary Period Badge */}
      {summary && (
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-sm">
            <Calendar className="mr-1 h-3 w-3" />
            {formatDate(summary.period_start)} - {formatDate(summary.period_end)}
          </Badge>
          <span className="text-sm text-muted-foreground">
            {summary.unique_sessions} unique sessions
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
            title="Total Searches"
            value={summary.total_searches.toLocaleString()}
            icon={Search}
            description={`${summary.unique_sessions} sessions`}
            color="blue"
          />
          <MetricCard
            title="Property Views"
            value={summary.total_property_views.toLocaleString()}
            icon={Eye}
            description="Properties viewed"
            color="green"
          />
          <MetricCard
            title="Tools Used"
            value={summary.total_tool_uses.toLocaleString()}
            icon={Wrench}
            description="Calculator & analysis tools"
            color="purple"
          />
          <MetricCard
            title="Avg Response Time"
            value={formatDuration(summary.avg_processing_time_ms)}
            icon={Clock}
            description="Processing time"
            color="amber"
          />
        </div>
      ) : null}

      {/* Additional Metrics Row */}
      {summary && !loading && (
        <div className="grid gap-4 md:grid-cols-3">
          <MetricCard
            title="Property Clicks"
            value={summary.total_property_clicks.toLocaleString()}
            icon={MousePointerClick}
            description="Click-through rate"
            color="pink"
          />
          <MetricCard
            title="Exports"
            value={summary.total_exports.toLocaleString()}
            icon={Download}
            description="Data exported"
            color="blue"
          />
          <MetricCard
            title="Favorites"
            value={summary.total_favorites.toLocaleString()}
            icon={Star}
            description="Properties saved"
            color="amber"
          />
        </div>
      )}

      {/* Charts Section */}
      <Tabs defaultValue="trends" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trends">
            <TrendingUp className="mr-2 h-4 w-4" />
            Activity Trends
          </TabsTrigger>
          <TabsTrigger value="tools">
            <Wrench className="mr-2 h-4 w-4" />
            Top Tools
          </TabsTrigger>
          <TabsTrigger value="cities">
            <MapPin className="mr-2 h-4 w-4" />
            Top Cities
          </TabsTrigger>
          <TabsTrigger value="daily">
            <BarChart3 className="mr-2 h-4 w-4" />
            Daily Activity
          </TabsTrigger>
        </TabsList>

        {/* Trends Tab */}
        <TabsContent value="trends" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Activity Over Time</CardTitle>
              <CardDescription>Your usage trends grouped by {interval}</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-72 w-full" />
              ) : trendsChartData.length > 0 ? (
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
                      dataKey="Searches"
                      stroke={CHART_COLORS[0]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="Property Views"
                      stroke={CHART_COLORS[1]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="Tool Uses"
                      stroke={CHART_COLORS[2]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="Exports"
                      stroke={CHART_COLORS[3]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-72 text-muted-foreground">
                  No trend data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tools Tab */}
        <TabsContent value="tools" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Most Used Tools</CardTitle>
              <CardDescription>Your favorite analysis and calculation tools</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-72 w-full" />
              ) : topToolsData.length > 0 ? (
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
              ) : (
                <div className="flex flex-col items-center justify-center h-72 text-muted-foreground">
                  <Wrench className="h-12 w-12 mb-4" />
                  <p>No tool usage data yet</p>
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
                <CardTitle>Top Search Cities</CardTitle>
                <CardDescription>Most searched locations</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-72 w-full" />
                ) : topCitiesData.length > 0 ? (
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
                ) : (
                  <div className="flex flex-col items-center justify-center h-72 text-muted-foreground">
                    <MapPin className="h-12 w-12 mb-4" />
                    <p>No city data yet</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* City Distribution Pie Chart */}
            {topCitiesData.length > 0 && !loading && (
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle>Search Distribution</CardTitle>
                  <CardDescription>Percentage of searches by city</CardDescription>
                </CardHeader>
                <CardContent>
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
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Daily Activity Tab */}
        <TabsContent value="daily" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Daily Activity</CardTitle>
              <CardDescription>Events per day over the selected period</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-72 w-full" />
              ) : dailyEventsData.length > 0 ? (
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
              ) : (
                <div className="flex flex-col items-center justify-center h-72 text-muted-foreground">
                  <BarChart3 className="h-12 w-12 mb-4" />
                  <p>No daily activity data yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
