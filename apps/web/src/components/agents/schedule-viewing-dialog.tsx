'use client';

import { useState } from 'react';
import { Clock, Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { scheduleViewing } from '@/lib/api';
import type { AgentProfile } from '@/lib/types';

/**
 * The viewing-request dialog.
 *
 * The prototype opens it as a dialog over the page: a scrim, a panel, and
 * the request itself. It says which listing the request is about, asks for
 * the date and the time the reader wants, and confirms in the agent's own
 * words that the appointment is a request - the agent confirms it.
 */

interface ScheduleViewingDialogProps {
  agent: AgentProfile;
  propertyId: string;
  /** The listing the request is about, in one line. */
  about?: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

const TIME_SLOTS = [
  '09:00',
  '09:30',
  '10:00',
  '10:30',
  '11:00',
  '11:30',
  '12:00',
  '12:30',
  '13:00',
  '13:30',
  '14:00',
  '14:30',
  '15:00',
  '15:30',
  '16:00',
  '16:30',
  '17:00',
  '17:30',
  '18:00',
];

export function ScheduleViewingDialog({
  agent,
  propertyId,
  about,
  onSuccess,
  onCancel,
}: ScheduleViewingDialogProps) {
  const t = useTranslations();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [booked, setBooked] = useState<{ date: string; time: string; minutes: number } | null>(
    null
  );

  const [formData, setFormData] = useState({
    client_name: '',
    client_email: '',
    client_phone: '',
    date: '',
    time: '10:00',
    duration_minutes: 30,
    notes: '',
  });

  const displayName =
    agent.name || agent.professional_email?.split('@')[0] || t('agents.profile.defaultName');

  const today = new Date().toISOString().split('T')[0];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const proposed_datetime = new Date(`${formData.date}T${formData.time}`);

      await scheduleViewing(agent.id, {
        property_id: propertyId,
        proposed_datetime: proposed_datetime.toISOString(),
        duration_minutes: formData.duration_minutes,
        client_name: formData.client_name,
        client_email: formData.client_email,
        client_phone: formData.client_phone || undefined,
        notes: formData.notes || undefined,
      });

      setBooked({
        date: formData.date,
        time: formData.time,
        minutes: formData.duration_minutes,
      });
      setSuccess(true);
      setTimeout(() => {
        onSuccess?.();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('scheduleViewing.failed'));
    } finally {
      setLoading(false);
    }
  };

  const fieldClass =
    'flex h-9 w-full rounded-md border border-input bg-background px-2.5 text-[14px] text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50';

  return (
    <div className="fixed inset-0 z-[2500] grid place-items-center bg-foreground/45 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t('scheduleViewing.title')}
        className="flex max-h-[90vh] w-full max-w-[480px] flex-col gap-3 overflow-y-auto rounded-xl border border-border bg-background p-5 shadow-[0_16px_48px_rgb(9_9_11/0.25)]"
      >
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-[17px] font-semibold text-foreground">
            {t('scheduleViewing.title')}
          </span>
          <button
            type="button"
            onClick={onCancel}
            aria-label={t('scheduleViewing.close')}
            className="border-0 bg-transparent p-0 text-[20px] leading-none text-muted-foreground hover:text-foreground"
          >
            &times;
          </button>
        </div>

        {success && booked ? (
          <div className="flex flex-col gap-1.5 py-2">
            <span className="text-[15px] font-semibold text-success">
              {t('scheduleViewing.successTitle')}
            </span>
            <span className="text-[14px] leading-5 text-muted-foreground">
              {t('scheduleViewing.successDetail', {
                date: booked.date,
                time: booked.time,
                minutes: booked.minutes,
              })}
            </span>
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              className="mt-2 h-9 self-end px-3.5 text-[14px]"
            >
              {t('scheduleViewing.close')}
            </Button>
          </div>
        ) : (
          <>
            <span className="text-[14px] leading-5 text-muted-foreground">
              {t('scheduleViewing.requestWith', { name: displayName })}
            </span>

            {about ? (
              <span className="rounded-md bg-muted px-2.5 py-2 text-[13px] text-foreground">
                {about}
              </span>
            ) : null}

            <form onSubmit={handleSubmit} className="flex flex-col gap-2.5">
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                <label className="flex flex-col gap-1">
                  <span className="text-[12px] font-medium text-foreground">
                    {t('scheduleViewing.nameLabel')}
                  </span>
                  <input
                    id="viewing-name"
                    type="text"
                    value={formData.client_name}
                    onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
                    required
                    className={fieldClass}
                  />
                </label>

                <label className="flex flex-col gap-1">
                  <span className="text-[12px] font-medium text-foreground">
                    {t('scheduleViewing.emailLabel')}
                  </span>
                  <input
                    id="viewing-email"
                    type="email"
                    value={formData.client_email}
                    onChange={(e) => setFormData({ ...formData, client_email: e.target.value })}
                    required
                    className={fieldClass}
                  />
                </label>

                <label className="flex flex-col gap-1">
                  <span className="text-[12px] font-medium text-foreground">
                    {t('scheduleViewing.dateLabel')}
                  </span>
                  <input
                    id="viewing-date"
                    type="date"
                    value={formData.date}
                    min={today}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    required
                    className={fieldClass}
                  />
                </label>

                <label className="flex flex-col gap-1">
                  <span className="text-[12px] font-medium text-foreground">
                    {t('scheduleViewing.timeLabel')}
                  </span>
                  <select
                    id="viewing-time"
                    value={formData.time}
                    onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                    required
                    className={fieldClass}
                  >
                    {TIME_SLOTS.map((slot) => (
                      <option key={slot} value={slot}>
                        {slot}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="flex flex-col gap-1">
                  <span className="text-[12px] font-medium text-foreground">
                    {t('scheduleViewing.phoneLabel')}
                  </span>
                  <input
                    id="viewing-phone"
                    type="tel"
                    value={formData.client_phone}
                    onChange={(e) => setFormData({ ...formData, client_phone: e.target.value })}
                    className={fieldClass}
                  />
                </label>

                <label className="flex flex-col gap-1">
                  <span className="text-[12px] font-medium text-foreground">
                    {t('scheduleViewing.durationLabel')}
                  </span>
                  <input
                    id="viewing-duration"
                    type="number"
                    value={formData.duration_minutes}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        duration_minutes: parseInt(e.target.value) || 30,
                      })
                    }
                    min={15}
                    max={120}
                    step={15}
                    className={`${fieldClass} font-mono`}
                  />
                </label>
              </div>

              <label className="flex flex-col gap-1">
                <span className="text-[12px] font-medium text-foreground">
                  {t('scheduleViewing.notesLabel')}
                </span>
                <textarea
                  id="viewing-notes"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder={t('scheduleViewing.notesPlaceholder')}
                  rows={2}
                  className="flex w-full resize-y rounded-md border border-input bg-background px-2.5 py-2 text-[14px] leading-5 text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                />
              </label>

              {error ? (
                <span className="text-[13px] text-destructive" role="alert">
                  {error}
                </span>
              ) : null}

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={onCancel} className="h-9 px-3.5">
                  {t('scheduleViewing.cancel')}
                </Button>
                <Button type="submit" disabled={loading} className="h-9 px-4">
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                      {t('scheduleViewing.requesting')}
                    </>
                  ) : (
                    <>
                      <Clock className="mr-2 h-4 w-4" aria-hidden="true" />
                      {t('scheduleViewing.submit')}
                    </>
                  )}
                </Button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
