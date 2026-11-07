'use client';

import { useState } from 'react';
import { Send, Loader2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { contactAgent } from '@/lib/api';
import { useLeadTracking } from '@/hooks/useLeadTracking';
import type { AgentProfile, InquiryType } from '@/lib/types';

interface ContactAgentFormProps {
  agent: AgentProfile;
  propertyId?: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

const inquiryTypes: { value: InquiryType; label: string }[] = [
  { value: 'general', label: 'General Inquiry' },
  { value: 'property', label: 'Property Inquiry' },
  { value: 'financing', label: 'Financing Options' },
  { value: 'viewing', label: 'Schedule Viewing' },
];

export function ContactAgentForm({
  agent,
  propertyId,
  onSuccess,
  onCancel,
}: ContactAgentFormProps) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { trackInteraction } = useLeadTracking();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    inquiry_type: 'general' as InquiryType,
    message: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await contactAgent(agent.id, {
        name: formData.name,
        email: formData.email,
        phone: formData.phone || undefined,
        inquiry_type: formData.inquiry_type,
        message: formData.message,
        property_id: propertyId,
      });

      // Lead tracking: record the inquiry (best-effort, never breaks the form).
      try {
        await trackInteraction({
          interaction_type: 'inquiry',
          property_id: propertyId,
          metadata: {
            agent_id: agent.id,
            inquiry_type: formData.inquiry_type,
            has_message: Boolean(formData.message),
          },
        });
      } catch {
        // ignore — telemetry must not surface as a form failure
      }

      setSuccess(true);
      setTimeout(() => {
        onSuccess?.();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const displayName = agent.name || agent.professional_email?.split('@')[0] || 'Agent';

  if (success) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-8 text-center">
          <div className="mb-4 rounded-full bg-green-100 p-3">
            <Send className="h-6 w-6 text-green-600" />
          </div>
          <h3 className="mb-2 text-lg font-semibold">Message Sent!</h3>
          <p className="text-muted-foreground">The agent will get back to you soon.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Contact {displayName}</CardTitle>
        {onCancel && (
          <Button variant="ghost" size="icon" onClick={onCancel} aria-label="Close form">
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        )}
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          Send a message to this agent. They will respond to your inquiry as soon as possible.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">Your Name *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="John Doe"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Your Email *</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="john@example.com"
                required
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="phone">Your Phone</Label>
              <Input
                id="phone"
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+1 234 567 8900"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="inquiry_type">Inquiry Type</Label>
              <Select
                value={formData.inquiry_type}
                onValueChange={(value: InquiryType) =>
                  setFormData({ ...formData, inquiry_type: value })
                }
              >
                <SelectTrigger id="inquiry_type">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {inquiryTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="message">Message *</Label>
            <textarea
              id="message"
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              placeholder="Tell us how we can help you..."
              rows={4}
              required
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          {error && (
            <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive" role="alert">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2">
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            )}
            <Button type="submit" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" aria-hidden="true" />
                  Send Message
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
