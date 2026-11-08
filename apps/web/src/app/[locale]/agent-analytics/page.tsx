'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import {
  Activity,
  ArrowDown,
  ArrowUp,
  Award,
  Briefcase,
  DollarSign,
  Target,
  TrendingUp,
  Users,
  Clock,
  Star,
  Lightbulb,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/ui/page-header';
import {
  getAgentMetrics,
  getTeamComparison,
  getPerformanceTrends,
  getCoachingInsights,
  getGoalProgress,
} from '@/lib/api';
import type {
  AgentMetrics,
  TeamComparison,
  PerformanceTrendPoint,
  CoachingInsight,
  GoalProgress,
} from '@/lib/types';

// Color coding for percentages
const getChangeColor = (value: number | null): string => {
  if (value === null) return 'text-muted-foreground';
  return value >= 0 ? 'text-success' : 'text-destructive';
};

const getChangeIcon = (value: number | null) => {
  if (value === null) return null;
  return value >= 0 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />;
};

// Metric Card Component
function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  change,
  format = 'number',
}: {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: React.ElementType;
  change?: number | null;
  format?: 'number' | 'currency' | 'percent' | 'days';
}) {
  const locale = useLocale();
  const formattedValue = (() => {
    if (typeof value === 'string') return value;
    switch (format) {
      case 'currency':
        return new Intl.NumberFormat(locale, {
          style: 'currency',
          currency: 'EUR',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(value);
      case 'percent':
        return `${value.toFixed(1)}%`;
      case 'days':
        return new Intl.NumberFormat(locale, {
          style: 'unit',
          unit: 'day',
          maximumFractionDigits: 1,
        }).format(value);
      default:
        return new Intl.NumberFormat(locale).format(value);
    }
  })();

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{formattedValue}</div>
        {(subtitle || change !== undefined) && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            {change !== null && change !== undefined && (
              <span className={`flex items-center ${getChangeColor(change)}`}>
                {getChangeIcon(change)}
                {Math.abs(change).toFixed(1)}%
              </span>
            )}
            {subtitle && <span>{subtitle}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Team Comparison Card
function TeamComparisonCard({ comparison }: { comparison: TeamComparison | null }) {
  const t = useTranslations('pages.agentAnalytics.team');

  if (!comparison) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('title')}</CardTitle>
          <CardDescription>{t('loading')}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const ranks = [
    { labelKey: 'deals', rank: comparison.rank_by_deals, total: comparison.total_agents },
    { labelKey: 'revenue', rank: comparison.rank_by_revenue, total: comparison.total_agents },
    { labelKey: 'conversion', rank: comparison.rank_by_conversion, total: comparison.total_agents },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Award className="h-5 w-5" />
          {t('title')}
        </CardTitle>
        <CardDescription>{t('vsAverage', { count: comparison.total_agents })}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          {ranks.map((item) => (
            <div key={item.labelKey} className="text-center">
              <div className="text-2xl font-bold">#{item.rank}</div>
              <div className="text-xs text-muted-foreground">
                {t('rankOf', { total: item.total, label: t(`labels.${item.labelKey}`) })}
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-3 pt-4 border-t">
          <ComparisonRow
            label={t('labels.deals')}
            vsAvg={comparison.deals_vs_avg_percent}
            avg={comparison.team_avg_deals}
            format="number"
          />
          <ComparisonRow
            label={t('labels.revenue')}
            vsAvg={comparison.revenue_vs_avg_percent}
            avg={comparison.team_avg_revenue}
            format="currency"
          />
          <ComparisonRow
            label={t('labels.conversion')}
            vsAvg={comparison.conversion_vs_avg_percent}
            avg={comparison.team_avg_conversion}
            format="percent"
          />
        </div>
      </CardContent>
    </Card>
  );
}

function ComparisonRow({
  label,
  vsAvg,
  avg,
  format,
}: {
  label: string;
  vsAvg: number;
  avg: number;
  format: 'number' | 'currency' | 'percent';
}) {
  const locale = useLocale();
  const t = useTranslations('pages.agentAnalytics.team');
  const formattedAvg = (() => {
    switch (format) {
      case 'currency':
        return new Intl.NumberFormat(locale, {
          style: 'currency',
          currency: 'EUR',
          minimumFractionDigits: 0,
        }).format(avg);
      case 'percent':
        return `${avg.toFixed(1)}%`;
      default:
        return avg.toFixed(1);
    }
  })();

  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-xs">{t('teamAvg', { value: formattedAvg })}</span>
        <span className={`flex items-center ${getChangeColor(vsAvg)}`}>
          {getChangeIcon(vsAvg)}
          {Math.abs(vsAvg).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

// Coaching Insights Panel
function CoachingInsightsPanel({ insights }: { insights: CoachingInsight[] }) {
  const t = useTranslations('pages.agentAnalytics.insights');
  const categoryConfig = {
    strength: { icon: Star, color: 'text-warning', bg: 'bg-warning/10', label: t('strength') },
    improvement: {
      icon: AlertCircle,
      color: 'text-destructive',
      bg: 'bg-destructive/10',
      label: t('improvement'),
    },
    opportunity: {
      icon: Lightbulb,
      color: 'text-info',
      bg: 'bg-info/10',
      label: t('opportunity'),
    },
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5" />
          {t('title')}
        </CardTitle>
        <CardDescription>{t('description')}</CardDescription>
      </CardHeader>
      <CardContent>
        {insights.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t('empty')}</p>
        ) : (
          <div className="space-y-3">
            {insights.slice(0, 5).map((insight, index) => {
              const config = categoryConfig[insight.category as keyof typeof categoryConfig];
              const Icon = config.icon;
              return (
                <div key={index} className={`p-3 rounded-lg ${config.bg} border`}>
                  <div className="flex items-start gap-3">
                    <Icon className={`h-5 w-5 mt-0.5 ${config.color}`} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{insight.title}</span>
                        <Badge variant="outline" className="text-xs">
                          {config.label}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">{insight.description}</p>
                      <p className="text-sm font-medium mt-2 text-primary">
                        → {insight.actionable_recommendation}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Goal Progress Card
function GoalProgressCard({ goals }: { goals: GoalProgress[] }) {
  const t = useTranslations('pages.agentAnalytics.goals');

  if (goals.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            {t('title')}
          </CardTitle>
          <CardDescription>{t('emptyTitle')}</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{t('emptyDescription')}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Target className="h-5 w-5" />
          {t('progressTitle')}
        </CardTitle>
        <CardDescription>{t('progressDescription')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {goals.map((goal) => (
          <div key={goal.id} className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium capitalize">{goal.goal_type}</span>
                {goal.is_achieved && <CheckCircle className="h-4 w-4 text-success" />}
              </div>
              <span className="text-sm text-muted-foreground">
                {goal.progress_percent.toFixed(0)}%
              </span>
            </div>
            <Progress value={goal.progress_percent} className="h-2" />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {goal.current_value} / {goal.target_value}
              </span>
              <span>
                {goal.days_remaining > 0
                  ? t('daysLeft', { count: goal.days_remaining })
                  : t('periodEnded')}
              </span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// Performance Trends Chart (simplified without recharts for now)
function PerformanceTrendsCard({ trends }: { trends: PerformanceTrendPoint[] }) {
  const locale = useLocale();
  const t = useTranslations('pages.agentAnalytics.trends');

  if (trends.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            {t('title')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{t('loading')}</p>
        </CardContent>
      </Card>
    );
  }

  const maxDeals = Math.max(...trends.map((t) => t.deals_closed), 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          {t('title')}
        </CardTitle>
        <CardDescription>{t('lastMonths', { count: trends.length })}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Simple bar chart for deals */}
          <div>
            <div className="text-sm font-medium mb-2">{t('dealsClosed')}</div>
            <div className="flex items-end gap-1 h-24">
              {trends.map((trend, index) => (
                <div
                  key={index}
                  className="flex-1 bg-primary/20 hover:bg-primary/40 rounded-t transition-colors"
                  style={{
                    height: `${(trend.deals_closed / maxDeals) * 100}%`,
                    minHeight: trend.deals_closed > 0 ? '4px' : '0',
                  }}
                  title={t('chartTitle', { period: trend.period, count: trend.deals_closed })}
                />
              ))}
            </div>
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>{trends[0]?.period}</span>
              <span>{trends[trends.length - 1]?.period}</span>
            </div>
          </div>

          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-4 pt-4 border-t">
            <div className="text-center">
              <div className="text-lg font-bold">{trends.reduce((sum, t) => sum + t.leads, 0)}</div>
              <div className="text-xs text-muted-foreground">{t('totalLeads')}</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold">
                {trends.reduce((sum, t) => sum + t.deals_closed, 0)}
              </div>
              <div className="text-xs text-muted-foreground">{t('dealsClosed')}</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold">
                {new Intl.NumberFormat(locale, {
                  style: 'currency',
                  currency: 'EUR',
                  notation: 'compact',
                }).format(trends.reduce((sum, t) => sum + t.revenue, 0))}
              </div>
              <div className="text-xs text-muted-foreground">{t('totalRevenue')}</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Main Page Component
export default function AgentAnalyticsPage() {
  const t = useTranslations('pages.agentAnalytics');
  const [metrics, setMetrics] = useState<AgentMetrics | null>(null);
  const [comparison, setComparison] = useState<TeamComparison | null>(null);
  const [trends, setTrends] = useState<PerformanceTrendPoint[]>([]);
  const [insights, setInsights] = useState<CoachingInsight[]>([]);
  const [goals, setGoals] = useState<GoalProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [metricsData, comparisonData, trendsData, insightsData, goalsData] = await Promise.all([
        getAgentMetrics(),
        getTeamComparison(),
        getPerformanceTrends({ interval: 'month', periods: 12 }),
        getCoachingInsights(),
        getGoalProgress(),
      ]);

      setMetrics(metricsData);
      setComparison(comparisonData);
      setTrends(trendsData.trends);
      setInsights(insightsData.insights);
      setGoals(goalsData.goals);
    } catch (err) {
      console.error(t('errors.fetch'), err);
      setError(t('errors.load'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8 space-y-6">
        <p className="text-muted-foreground">{t('loading')}</p>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="h-16 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <PageHeader title={t('title')} description={t('pageDescription')} />

      {/* Overview Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title={t('metrics.totalLeads')}
          value={metrics?.total_leads ?? 0}
          subtitle={t('metrics.newThisWeek', { count: metrics?.new_leads_week ?? 0 })}
          icon={Users}
        />
        <MetricCard
          title={t('metrics.activeDeals')}
          value={metrics?.active_deals ?? 0}
          subtitle={t('metrics.closed', { count: metrics?.closed_deals ?? 0 })}
          icon={Briefcase}
        />
        <MetricCard
          title={t('metrics.conversionRate')}
          value={metrics?.overall_conversion_rate ?? 0}
          format="percent"
          subtitle={t('metrics.overall')}
          icon={Target}
        />
        <MetricCard
          title={t('metrics.totalRevenue')}
          value={metrics?.total_deal_value ?? 0}
          format="currency"
          change={metrics?.revenue_change_percent}
          icon={DollarSign}
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title={t('metrics.highValueLeads')}
          value={metrics?.high_value_leads ?? 0}
          subtitle={t('metrics.scoreAtLeast')}
          icon={Star}
        />
        <MetricCard
          title={t('metrics.avgTimeToClose')}
          value={metrics?.avg_time_to_close_days ?? '-'}
          format="days"
          icon={Clock}
        />
        <MetricCard
          title={t('metrics.avgDealValue')}
          value={metrics?.avg_deal_value ?? 0}
          format="currency"
          icon={Activity}
        />
        <MetricCard
          title={t('metrics.pendingCommission')}
          value={metrics?.pending_commission ?? 0}
          format="currency"
          icon={DollarSign}
        />
      </div>

      {/* Tabs for detailed views */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">{t('tabs.overview')}</TabsTrigger>
          <TabsTrigger value="insights">{t('tabs.insights')}</TabsTrigger>
          <TabsTrigger value="goals">{t('tabs.goals')}</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <PerformanceTrendsCard trends={trends} />
            <TeamComparisonCard comparison={comparison} />
          </div>

          {/* Strengths */}
          {(metrics?.top_property_types?.length ?? 0) > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t('strengths.title')}</CardTitle>
                <CardDescription>{t('strengths.description')}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <h4 className="text-sm font-medium mb-2">{t('strengths.propertyTypes')}</h4>
                    <div className="space-y-2">
                      {metrics?.top_property_types?.slice(0, 3).map((pt, i) => (
                        <div key={i} className="flex items-center justify-between text-sm">
                          <span>{pt.type}</span>
                          <Badge variant="secondary">{pt.percentage}%</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium mb-2">{t('strengths.locations')}</h4>
                    <div className="space-y-2">
                      {metrics?.top_locations?.slice(0, 3).map((loc, i) => (
                        <div key={i} className="flex items-center justify-between text-sm">
                          <span>{loc.location}</span>
                          <Badge variant="secondary">{loc.percentage}%</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="insights">
          <CoachingInsightsPanel insights={insights} />
        </TabsContent>

        <TabsContent value="goals">
          <GoalProgressCard goals={goals} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
