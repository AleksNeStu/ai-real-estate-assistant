'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
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

const INQUIRY_TYPE_LABEL_KEYS: Record<InquiryType, string> = {
  general: 'general',
  property: 'property',
  financing: 'financing',
  viewing: 'viewing',
};

export function ContactAgentForm({
  agent,
  propertyId,
  onSuccess,
  onCancel,
}: ContactAgentFormProps) {
  const t = useTranslations('agents.contactForm');
  const tAgents = useTranslations('agents');
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
      setError(err instanceof Error ? err.message : t('errors.send'));
    } finally {
      setLoading(false);
    }
  };

  const displayName =
    agent.name || agent.professional_email?.split('@')[0] || tAgents('profile.defaultName');

  if (success) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-8 text-center">
          <div className="mb-4 rounded-full bg-success/15 p-3">
            <Send className="h-6 w-6 text-success" />
          </div>
          <h3 className="mb-2 text-lg font-semibold">{t('successTitle')}</h3>
          <p className="text-muted-foreground">{t('successDescription')}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">{t('title', { name: displayName })}</CardTitle>
        {onCancel && (
          <Button variant="ghost" size="icon" onClick={onCancel} aria-label={t('closeAria')}>
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        )}
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">{t('intro')}</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">{t('name')} *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder={t('namePlaceholder')}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">{t('email')} *</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder={t('emailPlaceholder')}
                required
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="phone">{t('phone')}</Label>
              <Input
                id="phone"
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder={t('phonePlaceholder')}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="inquiry_type">{t('inquiryType')}</Label>
              <Select
                value={formData.inquiry_type}
                onValueChange={(value: InquiryType) =>
                  setFormData({ ...formData, inquiry_type: value })
                }
              >
                <SelectTrigger id="inquiry_type">
                  <SelectValue placeholder={t('typePlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(INQUIRY_TYPE_LABEL_KEYS) as InquiryType[]).map((type) => (
                    <SelectItem key={type} value={type}>
                      {t(INQUIRY_TYPE_LABEL_KEYS[type])}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="message">{t('message')} *</Label>
            <textarea
              id="message"
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              placeholder={t('messagePlaceholder')}
              rows={4}
              required
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
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
                {t('cancel')}
              </Button>
            )}
            <Button type="submit" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                  {t('sending')}
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" aria-hidden="true" />
                  {t('submit')}
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
