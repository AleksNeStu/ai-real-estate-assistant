'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { GraduationCap, ShoppingBag, Trees, MapPin, Shield, Bus, ExternalLink } from 'lucide-react';
import type { NeighborhoodQualityResult, NearbyPOI } from '@/lib/types';

interface WhatsNearbySectionProps {
  result: NeighborhoodQualityResult;
  className?: string;
  showMap?: boolean;
}

interface POICategory {
  key: keyof NonNullable<NeighborhoodQualityResult['nearby_pois']>;
  label: string;
  icon: React.ReactElement;
  description: string;
  color: string;
  bgColor: string;
}

/**
 * WhatsNearbySection Component
 *
 * Displays tabbed lists of nearby Points of Interest (POIs) by category:
 * - Schools
 * - Amenities (shops, restaurants, services)
 * - Green Spaces (parks, recreational areas)
 * - Transport Stops (bus, tram, metro, train)
 * - Police Stations (safety infrastructure)
 */
export function WhatsNearbySection({
  result,
  className = '',
  showMap = false,
}: WhatsNearbySectionProps) {
  const [activeTab, setActiveTab] = useState('schools');

  const nearbyPois = result.nearby_pois;

  if (!nearbyPois) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>What&apos;s Nearby</CardTitle>
          <CardDescription>Points of interest in the neighborhood</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <p className="text-sm">Nearby places data not available for this location.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const categories: POICategory[] = [
    {
      key: 'schools',
      label: 'Schools',
      icon: <GraduationCap className="h-4 w-4" aria-hidden="true" />,
      description: 'Educational institutions nearby',
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
    },
    {
      key: 'amenities',
      label: 'Amenities',
      icon: <ShoppingBag className="h-4 w-4" aria-hidden="true" />,
      description: 'Shops, restaurants, and services',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      key: 'green_spaces',
      label: 'Green Spaces',
      icon: <Trees className="h-4 w-4" aria-hidden="true" />,
      description: 'Parks and recreational areas',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      key: 'transport_stops',
      label: 'Transport',
      icon: <Bus className="h-4 w-4" aria-hidden="true" />,
      description: 'Public transport access points',
      color: 'text-rose-600',
      bgColor: 'bg-rose-50',
    },
    {
      key: 'police_stations',
      label: 'Safety',
      icon: <Shield className="h-4 w-4" aria-hidden="true" />,
      description: 'Police and emergency services',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
  ];

  const formatDistance = (meters: number): string => {
    if (meters < 1000) {
      return `${meters}m`;
    }
    return `${(meters / 1000).toFixed(1)}km`;
  };

  const getDistanceColor = (meters: number): string => {
    if (meters <= 500) return 'text-green-600';
    if (meters <= 1000) return 'text-yellow-600';
    return 'text-orange-600';
  };

  const getTotalCount = (): number => {
    return categories.reduce((sum, cat) => sum + (nearbyPois[cat.key]?.length || 0), 0);
  };

  const getNearestPOI = (): { name: string; distance: number; category: string } | null => {
    let result: { name: string; distance: number; category: string } | null = null;
    let minDistance = Infinity;

    categories.forEach((cat) => {
      const pois = nearbyPois[cat.key];
      if (pois) {
        pois.forEach((poi) => {
          if (poi.distance_meters < minDistance) {
            minDistance = poi.distance_meters;
            result = {
              name: poi.name,
              distance: poi.distance_meters,
              category: poi.category,
            };
          }
        });
      }
    });

    return result;
  };

  const nearestPOI = getNearestPOI();

  const renderPOIList = (pois: NearbyPOI[], category: POICategory) => {
    if (!pois || pois.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <div className={`p-3 rounded-full ${category.bgColor} ${category.color} opacity-50 mb-3`}>
            {category.icon}
          </div>
          <p className="text-sm">No {category.label.toLowerCase()} found nearby</p>
        </div>
      );
    }

    // Sort by distance
    const sortedPois = [...pois].sort((a, b) => a.distance_meters - b.distance_meters);

    return (
      <div className="space-y-2">
        {sortedPois.map((poi, index) => (
          <div
            key={`${poi.name}-${index}`}
            className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
          >
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className={`p-2 rounded-full ${category.bgColor} ${category.color} shrink-0`}>
                <MapPin className="h-3 w-3" aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium truncate">{poi.name}</p>
                <p className="text-xs text-muted-foreground truncate">{poi.category}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0 ml-2">
              <span className={`text-sm font-semibold ${getDistanceColor(poi.distance_meters)}`}>
                {formatDistance(poi.distance_meters)}
              </span>
              {poi.latitude && poi.longitude && (
                <a
                  href={`https://www.google.com/maps?q=${poi.latitude},${poi.longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded-md hover:bg-background transition-colors"
                  title="Open in Google Maps"
                >
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>What&apos;s Nearby</CardTitle>
            <CardDescription>Points of interest within walking distance</CardDescription>
          </div>
          {nearestPOI && (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Nearest Place</p>
              <p className="text-sm font-medium">{nearestPOI.name}</p>
              <p className={`text-xs font-semibold ${getDistanceColor(nearestPOI.distance)}`}>
                {formatDistance(nearestPOI.distance)}
              </p>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Summary stats */}
        <div className="flex flex-wrap items-center gap-4 mb-4 pb-4 border-b">
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <span className="text-sm">
              <span className="font-semibold">{getTotalCount()}</span> places nearby
            </span>
          </div>
          {categories.map((cat) => {
            const count = nearbyPois[cat.key]?.length || 0;
            if (count === 0) return null;
            return (
              <div key={cat.key} className="flex items-center gap-1">
                <span className={`text-xs ${cat.color}`}>{cat.icon}</span>
                <span className="text-xs text-muted-foreground">
                  {count} {cat.label.toLowerCase()}
                </span>
              </div>
            );
          })}
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-5">
            {categories.map((cat) => {
              const count = nearbyPois[cat.key]?.length || 0;
              return (
                <TabsTrigger
                  key={cat.key}
                  value={cat.key}
                  className="flex items-center gap-1.5 data-[state=active]:bg-background"
                  disabled={count === 0}
                >
                  {cat.icon}
                  <span className="hidden sm:inline">{cat.label}</span>
                  {count > 0 && (
                    <span className="ml-1 text-xs bg-muted px-1.5 py-0.5 rounded-full">
                      {count}
                    </span>
                  )}
                </TabsTrigger>
              );
            })}
          </TabsList>

          {categories.map((cat) => (
            <TabsContent key={cat.key} value={cat.key} className="mt-4">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className={`p-2 rounded-lg ${cat.bgColor} ${cat.color}`}>{cat.icon}</div>
                  <div>
                    <h4 className="font-semibold">{cat.label}</h4>
                    <p className="text-xs text-muted-foreground">{cat.description}</p>
                  </div>
                </div>
                {renderPOIList(nearbyPois[cat.key] || [], cat)}
              </div>
            </TabsContent>
          ))}
        </Tabs>

        {/* Map placeholder (for future integration) */}
        {showMap && result.latitude && result.longitude && (
          <div className="mt-4 pt-4 border-t">
            <div className="rounded-lg bg-muted h-48 flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <MapPin className="h-8 w-8 mx-auto mb-2" aria-hidden="true" />
                <p className="text-sm">Map preview is not available in this report</p>
                <p className="text-xs">
                  Coordinates: {result.latitude.toFixed(4)}, {result.longitude.toFixed(4)}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
