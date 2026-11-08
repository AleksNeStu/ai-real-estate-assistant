"use client";

import React from "react";
import { useTranslations } from 'next-intl';

interface NeighborhoodBadgeProps {
  overallScore: number;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

/**
 * Neighborhood Quality Badge Component
 *
 * Displays a color-coded badge showing neighborhood quality score.
 * Used on property cards, search results, and detail pages.
 *
 * Color coding:
 * - 85+ (Excellent): Green
 * - 70-84 (Good): Lime
 * - 55-69 (Fair): Yellow
 * - 40-54 (Poor): Orange
 * - <40 (Very Poor): Red
 */
export function NeighborhoodBadge({
  overallScore,
  showLabel = true,
  size = "md",
  className = "",
}: NeighborhoodBadgeProps) {
  const t = useTranslations('neighborhood');
  const getScoreColor = (): string => {
    if (overallScore >= 85) return "text-success";
    if (overallScore >= 70) return "text-chart-7";
    if (overallScore >= 55) return "text-warning";
    if (overallScore >= 40) return "text-caution";
    return "text-destructive";
  };

  const getBgColor = (): string => {
    if (overallScore >= 85) return "bg-success/10";
    if (overallScore >= 70) return "bg-chart-7/10";
    if (overallScore >= 55) return "bg-warning/10";
    if (overallScore >= 40) return "bg-caution/10";
    return "bg-destructive/10";
  };

  const getBorderColor = (): string => {
    if (overallScore >= 85) return "border-success/30";
    if (overallScore >= 70) return "border-chart-7/30";
    if (overallScore >= 55) return "border-warning/30";
    if (overallScore >= 40) return "border-caution/30";
    return "border-destructive/30";
  };

  const getRatingLabel = (): string => {
    if (overallScore >= 85) return t('score.excellent');
    if (overallScore >= 70) return t('score.good');
    if (overallScore >= 55) return t('score.fair');
    if (overallScore >= 40) return t('score.poor');
    return t('score.veryPoor');
  };

  const getRatingLabelShort = (): string => {
    if (overallScore >= 85) return t('score.short.exc');
    if (overallScore >= 70) return t('score.short.good');
    if (overallScore >= 55) return t('score.short.fair');
    if (overallScore >= 40) return t('score.short.poor');
    return t('score.short.vpoor');
  };

  const sizeClasses = {
    sm: {
      container: "px-2 py-0.5 text-xs",
      score: "text-sm font-semibold",
      label: "text-xs",
    },
    md: {
      container: "px-2.5 py-1 text-xs",
      score: "text-base font-semibold",
      label: "text-xs",
    },
    lg: {
      container: "px-3 py-1.5 text-sm",
      score: "text-lg font-bold",
      label: "text-sm",
    },
  };

  const classes = sizeClasses[size];
  const scoreColor = getScoreColor();
  const bgColor = getBgColor();
  const borderColor = getBorderColor();

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-full border ${bgColor} ${borderColor} ${classes.container} ${className}`}
      title={t('quality.badge', { rating: getRatingLabel(), score: overallScore })}
    >
      {/* Score */}
      <span className={`${scoreColor} ${classes.score}`}>
        {overallScore.toFixed(1)}
      </span>

      {/* Label */}
      {showLabel && (
        <span className={`${scoreColor} ${classes.label} font-medium`}>
          {getRatingLabelShort()}
        </span>
      )}
    </div>
  );
}

/**
 * Compact Neighborhood Badge
 *
 * Minimal version showing only the score circle with color indicator.
 * Useful for tight spaces like property card headers.
 */
interface NeighborhoodBadgeCircleProps {
  overallScore: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function NeighborhoodBadgeCircle({
  overallScore,
  size = "md",
  className = "",
}: NeighborhoodBadgeCircleProps) {
  const t = useTranslations('neighborhood');

  const getBadgeColors = (): { bg: string; text: string } => {
    if (overallScore >= 85) return { bg: "bg-success", text: "text-success-foreground" };
    if (overallScore >= 70) return { bg: "bg-chart-7", text: "text-chart-7-foreground" };
    if (overallScore >= 55) return { bg: "bg-warning", text: "text-warning-foreground" };
    if (overallScore >= 40) return { bg: "bg-caution", text: "text-caution-foreground" };
    return { bg: "bg-destructive", text: "text-destructive-foreground" };
  };

  const sizeClasses = {
    sm: "w-5 h-5 text-[10px]",
    md: "w-6 h-6 text-xs",
    lg: "w-8 h-8 text-sm",
  };

  const { bg, text } = getBadgeColors();

  return (
    <div
      className={`inline-flex items-center justify-center rounded-full ${bg} ${text} ${sizeClasses[size]} ${className}`}
      title={t('quality.score', { score: overallScore.toFixed(1) })}
    >
      {overallScore.toFixed(0)}
    </div>
  );
}

/**
 * Detailed Neighborhood Score Display
 *
 * Full breakdown display with all component scores.
 * Useful for detail pages and expanded views.
 */
interface NeighborhoodScoreDisplayProps {
  result: {
    overall_score: number;
    safety_score: number;
    schools_score: number;
    amenities_score: number;
    walkability_score: number;
    green_space_score: number;
  };
  compact?: boolean;
  className?: string;
}

export function NeighborhoodScoreDisplay({
  result,
  compact = false,
  className = "",
}: NeighborhoodScoreDisplayProps) {
  const t = useTranslations('neighborhood');
  const getScoreColor = (score: number): string => {
    if (score >= 85) return "bg-success";
    if (score >= 70) return "bg-chart-7";
    if (score >= 55) return "bg-warning";
    if (score >= 40) return "bg-caution";
    return "bg-destructive";
  };

  const components = [
    { label: t('components.safety'), score: result.safety_score, weight: "25%" },
    { label: t('components.schools'), score: result.schools_score, weight: "20%" },
    { label: t('components.amenities'), score: result.amenities_score, weight: "20%" },
    { label: t('components.walkability'), score: result.walkability_score, weight: "20%" },
    { label: t('components.greenSpace'), score: result.green_space_score, weight: "15%" },
  ];

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Overall Score */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{t('overallScore')}</span>
        <NeighborhoodBadge
          overallScore={result.overall_score}
          size={compact ? "sm" : "md"}
        />
      </div>

      {/* Component Scores */}
      {!compact && (
        <div className="space-y-2">
          {components.map((component) => (
            <div
              key={component.label}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-muted-foreground">
                {component.label} <span className="text-muted-foreground">({component.weight})</span>
              </span>
              <div className="flex items-center gap-2">
                <div className="w-32 bg-muted rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${getScoreColor(component.score)}`}
                    style={{ width: `${component.score}%` }}
                  />
                </div>
                <span className="text-muted-foreground w-12 text-right">
                  {component.score.toFixed(1)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
