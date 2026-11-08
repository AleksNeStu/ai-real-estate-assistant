'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, CheckCircle, Info, ShieldAlert } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface RiskGaugeProps {
  score: number;
  riskFactors?: string[];
  recommendations?: string[];
  className?: string;
}

export function RiskGauge({
  score,
  riskFactors = [],
  recommendations = [],
  className,
}: RiskGaugeProps) {
  const t = useTranslations('investment');
  // Score is 0-100, where higher = lower risk
  const getRiskLevel = (s: number): { label: string; color: string; icon: React.ReactNode } => {
    if (s >= 80) {
      return {
        label: t('charts.risk.lowRisk'),
        color: 'text-success',
        icon: <CheckCircle className="h-6 w-6 text-success" />,
      };
    }
    if (s >= 60) {
      return {
        label: t('charts.risk.moderateRisk'),
        color: 'text-info',
        icon: <Info className="h-6 w-6 text-info" />,
      };
    }
    if (s >= 40) {
      return {
        label: t('charts.risk.elevatedRisk'),
        color: 'text-warning',
        icon: <AlertTriangle className="h-6 w-6 text-warning" />,
      };
    }
    return {
      label: t('charts.risk.highRisk'),
      color: 'text-destructive',
      icon: <ShieldAlert className="h-6 w-6 text-destructive" />,
    };
  };

  const riskLevel = getRiskLevel(score);

  // Calculate gauge rotation (-90 to 90 degrees maps to 0-100 score)
  const rotation = -90 + (score / 100) * 180;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {t('charts.risk.title')}
          <span aria-hidden="true">{riskLevel.icon}</span>
        </CardTitle>
        <CardDescription>{t('charts.risk.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Gauge Visualization */}
        <div
          className="flex flex-col items-center mb-6"
          role="img"
          aria-label={t('charts.risk.ariaLabel', { score, level: riskLevel.label })}
        >
          <div className="relative w-48 h-24 overflow-hidden">
            {/* Gauge background arc */}
            <div className="absolute inset-0 border-[16px] border-muted rounded-t-full" />
            {/* Gauge colored arc */}
            <div
              className="absolute inset-0 border-[16px] rounded-t-full"
              style={{
                borderColor:
                  score >= 80
                    ? 'hsl(var(--chart-2))'
                    : score >= 60
                      ? 'hsl(var(--chart-1))'
                      : score >= 40
                        ? 'hsl(var(--warning))'
                        : 'hsl(var(--chart-8))',
              }}
            />
            {/* Needle */}
            <div
              className="absolute bottom-0 left-1/2 w-1 h-16 bg-foreground origin-bottom"
              style={{
                transform: `translateX(-50%) rotate(${rotation}deg)`,
              }}
            />
            {/* Center dot */}
            <div className="absolute bottom-0 left-1/2 w-4 h-4 bg-foreground rounded-full -translate-x-1/2 translate-y-1/2" />
          </div>
          <div className="text-center mt-2">
            <p className={`text-3xl font-bold ${riskLevel.color}`}>{score}</p>
            <p className="text-sm text-muted-foreground">{t('charts.risk.outOf100')}</p>
            <p className={`text-lg font-semibold ${riskLevel.color}`}>{riskLevel.label}</p>
          </div>
        </div>

        {/* Risk Factors */}
        {riskFactors.length > 0 && (
          <div className="mb-4">
            <h4 className="text-sm font-medium mb-2">{t('charts.risk.riskFactors')}</h4>
            <ul className="space-y-1">
              {riskFactors.map((factor, index) => (
                <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-warning mt-0.5 shrink-0" />
                  {factor}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <div>
            <h4 className="text-sm font-medium mb-2">{t('charts.risk.recommendations')}</h4>
            <ul className="space-y-1">
              {recommendations.map((rec, index) => (
                <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 text-success mt-0.5 shrink-0" />
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
