'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  MapPin,
  Phone,
  Mail,
  Star,
  BadgeCheck,
  Building2,
  Briefcase,
  Calendar,
  Globe,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { getAgent, getAgentListings } from '@/lib/api';
import type { AgentProfile, AgentListing } from '@/lib/types';
import { ContactAgentForm } from '@/components/agents/contact-agent-form';
import { ScheduleViewingDialog } from '@/components/agents/schedule-viewing-dialog';
import { ErrorState } from '@/components/ui/states';

interface AgentProfilePageProps {
  params: Promise<{ locale: string; id: string }>;
}

export default function AgentProfilePage({ params }: AgentProfilePageProps) {
  // Unwrap params Promise using React.use()
  const resolvedParams = use(params);
  const agentId = resolvedParams.id;
  const locale = resolvedParams.locale;

  const [agent, setAgent] = useState<AgentProfile | null>(null);
  const [listings, setListings] = useState<AgentListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('about');
  const [showContactForm, setShowContactForm] = useState(false);
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string | null>(null);

  useEffect(() => {
    const loadAgent = async () => {
      try {
        setLoading(true);
        setError(null);

        const [agentData, listingsData] = await Promise.all([
          getAgent(agentId),
          getAgentListings(agentId),
        ]);

        setAgent(agentData);
        setListings(listingsData.items || []);
        if (listingsData.items?.length) {
          setSelectedPropertyId(listingsData.items[0].property_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load agent profile');
      } finally {
        setLoading(false);
      }
    };

    if (agentId) {
      loadAgent();
    }
  }, [agentId]);

  if (loading) {
    return (
      <div className="container mx-auto max-w-5xl px-4 py-8">
        <div className="flex items-center gap-2 mb-6">
          <Skeleton className="h-10 w-10 rounded-full" />
          <Skeleton className="h-6 w-32" />
        </div>
        <Card>
          <CardContent className="p-6">
            <div className="flex gap-6">
              <Skeleton className="h-24 w-24 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-64" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="container mx-auto max-w-5xl px-4 py-8">
        <Link href={`/${locale}/agents`}>
          <Button variant="ghost" size="sm" className="mb-6">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Agents
          </Button>
        </Link>
        <ErrorState
          title={error || 'Agent not found'}
          action={
            <Link href={`/${locale}/agents`}>
              <Button>Browse Agents</Button>
            </Link>
          }
        />
      </div>
    );
  }

  const displayName = agent.name || agent.professional_email?.split('@')[0] || 'Agent';
  const initials = displayName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      {/* Back Link */}
      <Link href={`/${locale}/agents`}>
        <Button variant="ghost" size="sm" className="mb-6">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Agents
        </Button>
      </Link>

      {/* Profile Header */}
      <Card className="mb-6">
        <CardContent className="p-6">
          <div className="flex flex-col gap-6 md:flex-row">
            {/* Avatar */}
            <div className="flex-shrink-0">
              {agent.profile_image_url ? (
                <img
                  src={agent.profile_image_url}
                  alt={displayName}
                  className="h-24 w-24 rounded-full object-cover"
                />
              ) : (
                <div className="flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-info to-critical text-2xl font-bold text-info-foreground">
                  {initials}
                </div>
              )}
            </div>

            {/* Info */}
            <div className="flex-1">
              <div className="flex flex-wrap items-start gap-2 mb-2">
                <h1 className="text-3xl font-semibold tracking-tight">{displayName}</h1>
                {agent.is_verified && (
                  <Badge variant="secondary" className="bg-success/15 text-success">
                    <BadgeCheck className="mr-1 h-3 w-3" />
                    Verified
                  </Badge>
                )}
              </div>

              {agent.agency_name && (
                <div className="flex items-center gap-2 text-muted-foreground mb-3">
                  <Building2 className="h-4 w-4" />
                  <span>{agent.agency_name}</span>
                </div>
              )}

              {/* Stats */}
              <div className="flex flex-wrap gap-4 text-sm mb-4">
                {agent.average_rating > 0 && (
                  <div className="flex items-center gap-1">
                    <Star className="h-4 w-4 fill-warning text-warning" />
                    <span className="font-medium">{agent.average_rating.toFixed(1)}</span>
                    <span className="text-muted-foreground">({agent.total_reviews} reviews)</span>
                  </div>
                )}
                <div className="flex items-center gap-1">
                  <Briefcase className="h-4 w-4" />
                  <span>{agent.total_sales} sales</span>
                </div>
                {agent.total_rentals > 0 && (
                  <div className="flex items-center gap-1">
                    <Briefcase className="h-4 w-4" />
                    <span>{agent.total_rentals} rentals</span>
                  </div>
                )}
              </div>

              {/* Specialties */}
              {agent.specialties && agent.specialties.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-4">
                  {agent.specialties.map((specialty) => (
                    <Badge key={specialty} variant="secondary">
                      {specialty}
                    </Badge>
                  ))}
                </div>
              )}

              {/* Service Areas */}
              {agent.service_areas && agent.service_areas.length > 0 && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                  <MapPin className="h-4 w-4" />
                  <span>{agent.service_areas.join(', ')}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => setShowContactForm(!showContactForm)}>
                  <Mail className="mr-2 h-4 w-4" />
                  Contact Agent
                </Button>
                {selectedPropertyId && (
                  <Button variant="outline" onClick={() => setShowScheduleForm(!showScheduleForm)}>
                    <Calendar className="mr-2 h-4 w-4" />
                    Schedule Viewing
                  </Button>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Contact Form (shown when button clicked) */}
      {showContactForm && (
        <div className="mb-6">
          <ContactAgentForm
            agent={agent}
            propertyId={selectedPropertyId || undefined}
            onSuccess={() => setShowContactForm(false)}
            onCancel={() => setShowContactForm(false)}
          />
        </div>
      )}

      {/* Schedule Form (shown when button clicked) */}
      {showScheduleForm && selectedPropertyId && (
        <div className="mb-6">
          <ScheduleViewingDialog
            agent={agent}
            propertyId={selectedPropertyId}
            onSuccess={() => setShowScheduleForm(false)}
            onCancel={() => setShowScheduleForm(false)}
          />
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="about">About</TabsTrigger>
          <TabsTrigger value="listings">Listings ({listings.length})</TabsTrigger>
          <TabsTrigger value="contact">Contact</TabsTrigger>
        </TabsList>

        <TabsContent value="about">
          <Card>
            <CardHeader>
              <CardTitle>About {displayName}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {agent.bio && (
                <p className="text-muted-foreground whitespace-pre-line">{agent.bio}</p>
              )}

              {!agent.bio && <p className="text-muted-foreground italic">No bio available.</p>}

              <Separator />

              {/* Languages */}
              {agent.languages && agent.languages.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <Globe className="h-4 w-4" />
                    Languages
                  </h4>
                  <div className="flex flex-wrap gap-1">
                    {agent.languages.map((lang) => (
                      <Badge key={lang} variant="outline">
                        {lang}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* License */}
              {agent.license_number && (
                <div>
                  <h4 className="font-medium mb-1">License</h4>
                  <p className="text-sm text-muted-foreground">
                    {agent.license_number}
                    {agent.license_state && ` (${agent.license_state})`}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="listings">
          <Card>
            <CardHeader>
              <CardTitle>Active Listings</CardTitle>
            </CardHeader>
            <CardContent>
              {listings.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">No active listings</p>
              ) : (
                <div className="space-y-4">
                  {listings.map((listing) => (
                    <div
                      key={listing.id}
                      className="flex items-center justify-between rounded-lg border p-4"
                    >
                      <div>
                        <p className="font-medium">{listing.property_id}</p>
                        <div className="flex gap-2 mt-1">
                          <Badge variant="outline">{listing.listing_type}</Badge>
                          {listing.is_primary && <Badge>Primary</Badge>}
                        </div>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedPropertyId(listing.property_id);
                          setShowScheduleForm(true);
                        }}
                      >
                        <Calendar className="mr-2 h-4 w-4" />
                        Schedule Viewing
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="contact">
          <Card>
            <CardHeader>
              <CardTitle>Contact Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {agent.professional_phone && (
                <div className="flex items-center gap-3">
                  <Phone className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Phone</p>
                    <a
                      href={`tel:${agent.professional_phone}`}
                      className="font-medium hover:underline"
                    >
                      {agent.professional_phone}
                    </a>
                  </div>
                </div>
              )}

              {agent.professional_email && (
                <div className="flex items-center gap-3">
                  <Mail className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Email</p>
                    <a
                      href={`mailto:${agent.professional_email}`}
                      className="font-medium hover:underline"
                    >
                      {agent.professional_email}
                    </a>
                  </div>
                </div>
              )}

              {agent.office_address && (
                <div className="flex items-center gap-3">
                  <MapPin className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Office</p>
                    <p className="font-medium">{agent.office_address}</p>
                  </div>
                </div>
              )}

              {agent.agency_name && (
                <div className="flex items-center gap-3">
                  <Building2 className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Agency</p>
                    <p className="font-medium">{agent.agency_name}</p>
                  </div>
                </div>
              )}

              <Separator />

              <div className="pt-2">
                <Button
                  className="w-full"
                  onClick={() => {
                    setActiveTab('about');
                    setShowContactForm(true);
                  }}
                >
                  <Mail className="mr-2 h-4 w-4" />
                  Send Message
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
