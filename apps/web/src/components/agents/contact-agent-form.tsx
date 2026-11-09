'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Send, Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
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

/**
 * The contact form of an agent.
 *
 * It sits in the sticky column of the profile, always visible, and it is
 * flat: fields, a rule, one action. The listing the reader has picked is
 * part of the form - the form says which listing it is about, so the agent
 * knows what the question is about without asking.
 *
 * The form says where the details go: to this agent only, to answer this
 * request. In demo mode the message is recorded, not e-mailed.
 */

interface ContactAgentFormProps {
  agent: AgentProfile;
  propertyId?: string;
  /** The listing the form is about, in one line. */
  about?: string;
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
  about,
  onSuccess,
  onCancel,
}: ContactAgentFormProps) {
  const t = useTranslations('agents.contactForm');
  const tAgents = useTranslations('agents');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [leadId, setLeadId] = useState<string | null>(null);
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
      const inquiry = await contactAgent(agent.id, {
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

      setLeadId(inquiry?.id ?? null);
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
      <div className="flex flex-col gap-1.5 rounded-lg border border-border p-4">
        <span className="text-[15px] font-semibold text-success">{t('successTitle')}</span>
        <span className="text-[14px] leading-5 text-muted-foreground">
          {leadId ? t('successLead', { name: displayName, id: leadId }) : t('successDescription')}
        </span>
      </div>
    );
  }

  const fieldClass =
    'flex h-[38px] w-full rounded-md border border-input bg-background px-2.5 text-[14px] text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50';

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2.5">
      <span className="text-[18px] font-semibold text-foreground">
        {t('title', { name: displayName })}
      </span>

      <label className="flex flex-col gap-1">
        <span className="text-[12px] font-medium text-foreground">{t('name')} *</span>
        <input
          id="contact-name"
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder={t('namePlaceholder')}
          required
          className={fieldClass}
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-[12px] font-medium text-foreground">{t('email')} *</span>
        <input
          id="contact-email"
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          placeholder={t('emailPlaceholder')}
          required
          className={fieldClass}
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-[12px] font-medium text-foreground">{t('phone')}</span>
        <input
          id="contact-phone"
          type="tel"
          value={formData.phone}
          onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
          placeholder={t('phonePlaceholder')}
          className={fieldClass}
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-[12px] font-medium text-foreground">{t('inquiryType')}</span>
        <Select
          value={formData.inquiry_type}
          onValueChange={(value: InquiryType) => setFormData({ ...formData, inquiry_type: value })}
        >
          <SelectTrigger id="inquiry_type" className="h-[38px] rounded-md">
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
      </label>

      {about ? (
        <div className="flex flex-col gap-1">
          <span className="text-[12px] font-medium text-foreground">{t('about')}</span>
          <span className="flex h-[38px] items-center rounded-md border border-border px-2.5 text-[13px] text-foreground">
            {about}
          </span>
        </div>
      ) : null}

      <label className="flex flex-col gap-1">
        <span className="text-[12px] font-medium text-foreground">{t('message')} *</span>
        <textarea
          id="contact-message"
          value={formData.message}
          onChange={(e) => setFormData({ ...formData, message: e.target.value })}
          placeholder={t('messagePlaceholder')}
          rows={4}
          required
          className="flex w-full resize-y rounded-md border border-input bg-background px-2.5 py-2 text-[14px] leading-5 text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        />
      </label>

      {error ? (
        <span className="text-[13px] text-destructive" role="alert">
          {error}
        </span>
      ) : null}

      <div className="flex items-center gap-2">
        <Button type="submit" disabled={loading} className="h-[42px]">
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
        {onCancel ? (
          <Button type="button" variant="outline" onClick={onCancel}>
            {t('cancel')}
          </Button>
        ) : null}
      </div>

      <span className="text-[12px] leading-[17px] text-muted-foreground">{t('privacyNote')}</span>
    </form>
  );
}
