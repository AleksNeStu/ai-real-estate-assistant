'use client';

import { useState, useEffect, useCallback } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { useTranslations } from 'next-intl';
import {
  Users,
  Download,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle,
  Clock,
  Star,
  Search,
  MoreHorizontal,
  Mail,
  Phone,
  Target,
  BarChart3,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/ui/page-header';

import {
  getLeads,
  getHighValueLeads,
  getScoringStatistics,
  updateLeadStatus,
  recalculateScores,
  exportLeads,
} from '@/lib/api';
import type { LeadWithScore, LeadFilters, LeadStatus, ScoringStatistics } from '@/lib/types';
import { EmptyState, ErrorState } from '@/components/ui/states';

// Score badge color mapping
function getScoreColor(score: number): string {
  if (score >= 80) return 'bg-success';
  if (score >= 60) return 'bg-info';
  if (score >= 40) return 'bg-warning';
  if (score >= 20) return 'bg-warning';
  return 'bg-muted-foreground';
}

function getScoreBadgeVariant(score: number): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (score >= 60) return 'default';
  if (score >= 40) return 'secondary';
  return 'outline';
}

// Status badge mapping
const statusConfig: Record<LeadStatus, { label: string; color: string; icon: typeof Star }> = {
  new: { label: 'New', color: 'bg-info/15 text-info', icon: AlertCircle },
  contacted: { label: 'Contacted', color: 'bg-warning/15 text-warning', icon: Mail },
  qualified: { label: 'Qualified', color: 'bg-success/15 text-success', icon: CheckCircle },
  converted: { label: 'Converted', color: 'bg-critical/20 text-critical', icon: Target },
  lost: { label: 'Lost', color: 'bg-muted text-foreground', icon: TrendingDown },
};

export default function LeadsPage() {
  const t = useTranslations('pages.leads');
  const [leads, setLeads] = useState<LeadWithScore[]>([]);
  const [highValueLeads, setHighValueLeads] = useState<LeadWithScore[]>([]);
  const [statistics, setStatistics] = useState<ScoringStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recalculating, setRecalculating] = useState(false);

  // Filters
  const [filters, setFilters] = useState<LeadFilters>({
    status: undefined,
    score_min: undefined,
    score_max: undefined,
    search: '',
    sort: 'score_desc',
    limit: 50,
    offset: 0,
  });

  // Load leads data
  const loadLeads = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [leadsResponse, highValueResponse, statsResponse] = await Promise.all([
        getLeads(filters),
        getHighValueLeads(70, 10),
        getScoringStatistics(),
      ]);

      setLeads(leadsResponse.items);
      setHighValueLeads(highValueResponse);
      setStatistics(statsResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leads');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadLeads();
  }, [loadLeads]);

  // Handle status update
  const handleStatusUpdate = async (leadId: string, status: LeadStatus) => {
    try {
      await updateLeadStatus(leadId, status);
      setLeads((prev) => prev.map((lead) => (lead.id === leadId ? { ...lead, status } : lead)));
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  // Handle recalculate scores
  const handleRecalculateScores = async () => {
    try {
      setRecalculating(true);
      await recalculateScores();
      await loadLeads();
    } catch (err) {
      console.error('Failed to recalculate scores:', err);
    } finally {
      setRecalculating(false);
    }
  };

  // Handle export
  const handleExport = async () => {
    try {
      const blob = await exportLeads(filters);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `leads-${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export leads:', err);
    }
  };

  // Format time ago
  const formatTimeAgo = (dateString: string) => {
    return formatDistanceToNow(new Date(dateString), { addSuffix: true });
  };

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <ErrorState title={error} onRetry={loadLeads} retryLabel="Try Again" />
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
            <Button variant="outline" onClick={handleExport}>
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
            <Button variant="outline" onClick={handleRecalculateScores} disabled={recalculating}>
              <RefreshCw className={`mr-2 h-4 w-4 ${recalculating ? 'animate-spin' : ''}`} />
              Recalculate Scores
            </Button>
          </div>
        }
      />

      {/* Statistics Cards */}
      {statistics && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Leads</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_leads}</div>
              <p className="text-xs text-muted-foreground">
                +{statistics.new_leads_24h} in last 24h
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">High Value Leads</CardTitle>
              <Star className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.high_value_leads}</div>
              <p className="text-xs text-muted-foreground">Score &gt; 70</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Average Score</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.avg_score.toFixed(1)}</div>
              <Progress value={statistics.avg_score} className="mt-2" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Conversion Rate</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.conversion_rate.toFixed(1)}%</div>
              <p className="text-xs text-muted-foreground">
                {statistics.converted_leads} converted
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">All Leads</TabsTrigger>
          <TabsTrigger value="high-value">High Value</TabsTrigger>
          <TabsTrigger value="new">New</TabsTrigger>
        </TabsList>

        {/* Filters */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-1 gap-2">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search leads..."
                value={filters.search || ''}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="pl-8"
              />
            </div>
            <Select
              value={filters.status || 'all'}
              onValueChange={(value) =>
                setFilters({
                  ...filters,
                  status: value === 'all' ? undefined : (value as LeadStatus),
                })
              }
            >
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="new">New</SelectItem>
                <SelectItem value="contacted">Contacted</SelectItem>
                <SelectItem value="qualified">Qualified</SelectItem>
                <SelectItem value="converted">Converted</SelectItem>
                <SelectItem value="lost">Lost</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={filters.sort || 'score_desc'}
              onValueChange={(value) => setFilters({ ...filters, sort: value })}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="score_desc">Score (High to Low)</SelectItem>
                <SelectItem value="score_asc">Score (Low to High)</SelectItem>
                <SelectItem value="last_activity">Recent Activity</SelectItem>
                <SelectItem value="created">Date Created</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* All Leads Tab */}
        <TabsContent value="all" className="space-y-4">
          {loading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <Card key={i}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-4">
                      <Skeleton className="h-12 w-12 rounded-full" />
                      <div className="flex-1 space-y-2">
                        <Skeleton className="h-4 w-[200px]" />
                        <Skeleton className="h-3 w-[150px]" />
                      </div>
                      <Skeleton className="h-8 w-20" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : leads.length === 0 ? (
            <EmptyState
              icon={Users}
              title="No leads found"
              description="Try adjusting your filters or wait for new leads to come in"
            />
          ) : (
            <div className="space-y-4">
              {leads.map((lead) => {
                const statusInfo = statusConfig[lead.status];
                const StatusIcon = statusInfo.icon;

                return (
                  <Card key={lead.id} className="hover:shadow-md transition-shadow">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-4">
                        {/* Avatar */}
                        <div className="flex-shrink-0">
                          <div className="h-12 w-12 rounded-full bg-gradient-to-br from-info to-critical flex items-center justify-center text-info-foreground font-semibold">
                            {lead.name?.charAt(0) || lead.email?.charAt(0) || '?'}
                          </div>
                        </div>

                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="font-medium truncate">{lead.name || 'Anonymous Lead'}</p>
                            <Badge variant={getScoreBadgeVariant(lead.total_score)}>
                              <Star className="mr-1 h-3 w-3" />
                              {lead.total_score}
                            </Badge>
                            <Badge className={statusInfo.color}>
                              <StatusIcon className="mr-1 h-3 w-3" />
                              {statusInfo.label}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                            {lead.email && (
                              <span className="flex items-center gap-1">
                                <Mail className="h-3 w-3" />
                                {lead.email}
                              </span>
                            )}
                            {lead.phone && (
                              <span className="flex items-center gap-1">
                                <Phone className="h-3 w-3" />
                                {lead.phone}
                              </span>
                            )}
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {formatTimeAgo(lead.last_activity_at)}
                            </span>
                          </div>
                        </div>

                        {/* Score Breakdown Mini */}
                        <div className="hidden md:flex items-center gap-2">
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground">Search</p>
                            <p className="font-medium">{lead.search_activity_score}</p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground">Engage</p>
                            <p className="font-medium">{lead.engagement_score}</p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground">Intent</p>
                            <p className="font-medium">{lead.intent_score}</p>
                          </div>
                        </div>

                        {/* Actions */}
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>View Details</DropdownMenuItem>
                            <DropdownMenuItem>Send Email</DropdownMenuItem>
                            <DropdownMenuItem>Schedule Call</DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => handleStatusUpdate(lead.id, 'contacted')}
                            >
                              Mark as Contacted
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => handleStatusUpdate(lead.id, 'qualified')}
                            >
                              Mark as Qualified
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => handleStatusUpdate(lead.id, 'converted')}
                            >
                              Mark as Converted
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => handleStatusUpdate(lead.id, 'lost')}>
                              Mark as Lost
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>

                      {/* Score Bar */}
                      <div className="mt-4">
                        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                          <span>Lead Score</span>
                          <span>{lead.total_score}/100</span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className={`h-full ${getScoreColor(lead.total_score)} transition-all`}
                            style={{ width: `${lead.total_score}%` }}
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        {/* High Value Tab */}
        <TabsContent value="high-value" className="space-y-4">
          {highValueLeads.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Star className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">No high-value leads</p>
                <p className="text-sm text-muted-foreground">
                  Leads with score above 70 will appear here
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {highValueLeads.map((lead) => (
                <Card key={lead.id} className="border-success/30 bg-success/10/50">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-success to-chart-7 flex items-center justify-center text-success-foreground font-semibold">
                          {lead.name?.charAt(0) || lead.email?.charAt(0) || '?'}
                        </div>
                        <div>
                          <p className="font-medium">{lead.name || 'Anonymous Lead'}</p>
                          <p className="text-sm text-muted-foreground">{lead.email}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge className="bg-success">
                          <Star className="mr-1 h-3 w-3" />
                          {lead.total_score}
                        </Badge>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatTimeAgo(lead.last_activity_at)}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* New Leads Tab */}
        <TabsContent value="new" className="space-y-4">
          {loading ? (
            <div className="flex justify-center py-8">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-4">
              {leads
                .filter((lead) => lead.status === 'new')
                .map((lead) => (
                  <Card key={lead.id} className="border-info/30">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-full bg-info/15 flex items-center justify-center">
                            <AlertCircle className="h-5 w-5 text-info" />
                          </div>
                          <div>
                            <p className="font-medium">{lead.name || 'New Lead'}</p>
                            <p className="text-sm text-muted-foreground">{lead.email}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant={getScoreBadgeVariant(lead.total_score)}>
                            Score: {lead.total_score}
                          </Badge>
                          <Button
                            size="sm"
                            onClick={() => handleStatusUpdate(lead.id, 'contacted')}
                          >
                            Contact
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
