'use client';

import { useEffect, useState } from 'react';
import { Bell, Smartphone, Mail, Monitor } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { MonoAnnotation } from '../ui/mono-annotation';
import { SettingsPanel, SettingsRow } from './settings-panel';
import {
  getNotificationSettings,
  updateNotificationSettings,
  sendNotificationPreview,
} from '@/lib/api';
import {
  NotificationSettings as SettingsType,
  NotificationSettingsUpdate,
  NotificationPreviewRequest,
} from '@/lib/types';
import {
  isPushSupported,
  requestNotificationPermission,
  getNotificationPermission,
} from '@/lib/push';

const DAYS_OF_WEEK = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];

/**
 * What reaches the inbox.
 *
 * The kinds of alert and the channels they travel over are two lists, so
 * they are two ledgers: one rule opens each and every row is one switch
 * with the label that says what it is. The times are values, so they are
 * mono.
 */
export function NotificationSettings({ userEmail }: { userEmail: string | null }) {
  const [settings, setSettings] = useState<SettingsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [pushPermissionStatus, setPushPermissionStatus] = useState<NotificationPermission | null>(
    null
  );
  const [sendingPreview, setSendingPreview] = useState(false);
  const t = useTranslations('settings');
  const tWeekdays = useTranslations('shellComponents.weekdays');

  useEffect(() => {
    if (!userEmail) {
      setLoading(false);
      return;
    }
    fetchSettings();
    checkPushStatus();
  }, [userEmail]);

  const fetchSettings = async () => {
    try {
      const data = await getNotificationSettings();
      setSettings(data);
      setError(null);
    } catch {
      setError(t('notifications.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  const checkPushStatus = async () => {
    if (isPushSupported()) {
      const status = await getNotificationPermission();
      setPushPermissionStatus(status);
    }
  };

  if (!userEmail) {
    return (
      <SettingsPanel title={t('notifications.title')} description={t('emailRequired')}>
        <div />
      </SettingsPanel>
    );
  }

  if (loading) {
    return (
      <SettingsPanel title={t('notifications.title')} description={t('notifications.loadingSettings')}>
        <div />
      </SettingsPanel>
    );
  }

  if (!settings) {
    return (
      <SettingsPanel title={t('notifications.title')} description={error || t('notifications.somethingWentWrong')}>
        <div className="flex items-center gap-3 py-4">
          <Button onClick={fetchSettings} variant="outline" size="sm">
            {t('notifications.retry')}
          </Button>
        </div>
      </SettingsPanel>
    );
  }

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const updateData: NotificationSettingsUpdate = {
        price_alerts_enabled: settings.price_alerts_enabled,
        new_listings_enabled: settings.new_listings_enabled,
        saved_search_enabled: settings.saved_search_enabled,
        market_updates_enabled: settings.market_updates_enabled,
        alert_frequency: settings.alert_frequency,
        email_enabled: settings.email_enabled,
        push_enabled: settings.push_enabled,
        in_app_enabled: settings.in_app_enabled,
        quiet_hours_start: settings.quiet_hours_start,
        quiet_hours_end: settings.quiet_hours_end,
        price_drop_threshold: settings.price_drop_threshold,
        daily_digest_time: settings.daily_digest_time,
        weekly_digest_day: settings.weekly_digest_day,
        expert_mode: settings.expert_mode,
        marketing_emails: settings.marketing_emails,
      };
      const updated = await updateNotificationSettings(updateData);
      setSettings(updated);
      setSuccess(t('saved'));
    } catch {
      setError(t('error'));
    } finally {
      setSaving(false);
    }
  };

  const toggleSetting = (key: keyof SettingsType) => {
    if (key === 'unsubscribe_token' || key === 'unsubscribed_at' || key === 'unsubscribed_types') {
      return;
    }
    setSettings({ ...settings, [key]: !settings[key] } as SettingsType);
  };

  const updateSetting = <K extends keyof SettingsType>(key: K, value: SettingsType[K]) => {
    setSettings({ ...settings, [key]: value });
  };

  const handleEnablePush = async () => {
    const permission = await requestNotificationPermission();
    setPushPermissionStatus(permission);
    if (permission === 'granted') {
      setSettings({ ...settings, push_enabled: true });
    }
  };

  const handleSendPreview = async (channel: 'email' | 'push' | 'in_app') => {
    setSendingPreview(true);
    setError(null);
    setSuccess(null);

    try {
      const request: NotificationPreviewRequest = {
        channel,
        notification_type: 'price_alert',
      };
      const result = await sendNotificationPreview(request);
      if (result.success) {
        setSuccess(result.message);
      } else {
        setError(result.message);
      }
    } catch {
      setError(t('notifications.sendPreviewFailed'));
    } finally {
      setSendingPreview(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <SettingsPanel
        title={t('notifications.notificationTypes')}
        description={t('notifications.notificationTypesDesc')}
      >
        <SettingsRow
          label={
            <Label htmlFor="price_alerts" className="cursor-pointer">
              {t('notifications.priceAlerts')}
            </Label>
          }
          description={t('notifications.priceAlertsDesc')}
          action={
            <input
              type="checkbox"
              id="price_alerts"
              className="h-4 w-4 rounded border-border"
              checked={settings.price_alerts_enabled}
              onChange={() => toggleSetting('price_alerts_enabled')}
            />
          }
        />

        <SettingsRow
          label={
            <Label htmlFor="new_listings" className="cursor-pointer">
              {t('notifications.newListings')}
            </Label>
          }
          description={t('notifications.newListingsDesc')}
          action={
            <input
              type="checkbox"
              id="new_listings"
              className="h-4 w-4 rounded border-border"
              checked={settings.new_listings_enabled}
              onChange={() => toggleSetting('new_listings_enabled')}
            />
          }
        />

        <SettingsRow
          label={
            <Label htmlFor="saved_search" className="cursor-pointer">
              {t('notifications.savedSearchUpdates')}
            </Label>
          }
          description={t('notifications.savedSearchUpdatesDesc')}
          action={
            <input
              type="checkbox"
              id="saved_search"
              className="h-4 w-4 rounded border-border"
              checked={settings.saved_search_enabled}
              onChange={() => toggleSetting('saved_search_enabled')}
            />
          }
        />

        <SettingsRow
          label={
            <Label htmlFor="market_updates" className="cursor-pointer">
              {t('notifications.marketUpdates')}
            </Label>
          }
          description={t('notifications.marketUpdatesDesc')}
          action={
            <input
              type="checkbox"
              id="market_updates"
              className="h-4 w-4 rounded border-border"
              checked={settings.market_updates_enabled}
              onChange={() => toggleSetting('market_updates_enabled')}
            />
          }
        />
      </SettingsPanel>

      <SettingsPanel
        title={t('notifications.channels')}
        description={t('notifications.channelsDesc')}
      >
        <SettingsRow
          label={
            <Label htmlFor="email_channel" className="flex cursor-pointer items-center gap-2">
              <Mail className="h-4 w-4" aria-hidden="true" />
              {t('notifications.emailChannel')}
            </Label>
          }
          description={t('notifications.emailChannelDesc')}
          action={
            <input
              type="checkbox"
              id="email_channel"
              className="h-4 w-4 rounded border-border"
              checked={settings.email_enabled}
              onChange={() => toggleSetting('email_enabled')}
            />
          }
        />

        <SettingsRow
          label={
            <Label htmlFor="push_channel" className="flex cursor-pointer items-center gap-2">
              <Smartphone className="h-4 w-4" aria-hidden="true" />
              {t('notifications.pushChannel')}
            </Label>
          }
          description={t('notifications.pushChannelDesc')}
          action={
            <input
              type="checkbox"
              id="push_channel"
              className="h-4 w-4 rounded border-border"
              checked={settings.push_enabled}
              onChange={() => toggleSetting('push_enabled')}
              disabled={pushPermissionStatus === 'denied'}
            />
          }
        />

        {pushPermissionStatus === 'default' && settings.push_enabled ? (
          <SettingsRow label={t('notifications.enablePushBrowser')}>
            <Button size="sm" onClick={handleEnablePush}>
              <Bell className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('notifications.enablePush')}
            </Button>
          </SettingsRow>
        ) : null}

        {pushPermissionStatus === 'denied' ? (
          <SettingsRow label={t('notifications.pushBlocked')}>
            <MonoAnnotation tone="destructive">{t('notifications.pushBlocked')}</MonoAnnotation>
          </SettingsRow>
        ) : null}

        <SettingsRow
          label={
            <Label htmlFor="in_app_channel" className="flex cursor-pointer items-center gap-2">
              <Monitor className="h-4 w-4" aria-hidden="true" />
              {t('notifications.inAppChannel')}
            </Label>
          }
          description={t('notifications.inAppChannelDesc')}
          action={
            <input
              type="checkbox"
              id="in_app_channel"
              className="h-4 w-4 rounded border-border"
              checked={settings.in_app_enabled}
              onChange={() => toggleSetting('in_app_enabled')}
            />
          }
        />
      </SettingsPanel>

      <SettingsPanel
        title={t('notifications.frequencyDigest')}
        description={t('notifications.frequencyDigestDesc')}
      >
        <SettingsRow label={t('notifications.alertFrequency')}>
          <select
            id="alert_frequency"
            aria-label={t('notifications.alertFrequency')}
            className="h-8 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
            value={settings.alert_frequency}
            onChange={(e) =>
              updateSetting('alert_frequency', e.target.value as 'instant' | 'daily' | 'weekly')
            }
          >
            <option value="instant">{t('notifications.instant')}</option>
            <option value="daily">{t('notifications.dailyDigest')}</option>
            <option value="weekly">{t('notifications.weeklyDigest')}</option>
          </select>
        </SettingsRow>

        <SettingsRow label={t('notifications.dailyDigestTime')}>
          <input
            type="time"
            id="daily_digest_time"
            aria-label={t('notifications.dailyDigestTime')}
            className="h-8 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
            value={settings.daily_digest_time}
            onChange={(e) => updateSetting('daily_digest_time', e.target.value)}
          />
        </SettingsRow>

        <SettingsRow label={t('notifications.weeklyDigestDay')}>
          <select
            id="weekly_digest_day"
            aria-label={t('notifications.weeklyDigestDay')}
            className="h-8 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
            value={settings.weekly_digest_day}
            onChange={(e) => updateSetting('weekly_digest_day', e.target.value)}
          >
            {DAYS_OF_WEEK.map((day) => (
              <option key={day} value={day}>
                {tWeekdays(day)}
              </option>
            ))}
          </select>
        </SettingsRow>
      </SettingsPanel>

      <SettingsPanel
        title={t('notifications.advancedSettings')}
        description={t('notifications.advancedSettingsDesc')}
      >
        <SettingsRow label={t('notifications.quietHoursStart')}>
          <input
            type="time"
            id="quiet_hours_start"
            className="h-8 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
            value={settings.quiet_hours_start || ''}
            onChange={(e) => updateSetting('quiet_hours_start', e.target.value || null)}
          />
        </SettingsRow>

        <SettingsRow label={t('notifications.quietHoursEnd')}>
          <input
            type="time"
            id="quiet_hours_end"
            className="h-8 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
            value={settings.quiet_hours_end || ''}
            onChange={(e) => updateSetting('quiet_hours_end', e.target.value || null)}
          />
        </SettingsRow>

        <SettingsRow
          label={t('notifications.priceDropThreshold')}
          description={t('notifications.priceDropThresholdDesc')}
        >
          <input
            type="number"
            id="price_drop_threshold"
            min="1"
            max="50"
            step="0.5"
            className="h-8 w-24 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
            value={settings.price_drop_threshold}
            onChange={(e) => updateSetting('price_drop_threshold', parseFloat(e.target.value))}
          />
        </SettingsRow>

        <SettingsRow
          label={
            <Label htmlFor="expert_mode" className="cursor-pointer">
              {t('notifications.expertMode')}
            </Label>
          }
          description={t('notifications.expertModeDesc')}
          action={
            <input
              type="checkbox"
              id="expert_mode"
              className="h-4 w-4 rounded border-border"
              checked={settings.expert_mode}
              onChange={() => toggleSetting('expert_mode')}
            />
          }
        />

        <SettingsRow
          label={
            <Label htmlFor="marketing_emails" className="cursor-pointer">
              {t('notifications.productUpdates')}
            </Label>
          }
          description={t('notifications.productUpdatesDesc')}
          action={
            <input
              type="checkbox"
              id="marketing_emails"
              className="h-4 w-4 rounded border-border"
              checked={settings.marketing_emails}
              onChange={() => toggleSetting('marketing_emails')}
            />
          }
        />
      </SettingsPanel>

      <SettingsPanel
        title={t('notifications.testNotifications')}
        description={t('notifications.testNotificationsDesc')}
      >
        <SettingsRow label={t('notifications.testNotificationsDesc')}>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSendPreview('email')}
              disabled={sendingPreview || !settings.email_enabled}
            >
              <Mail className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('notifications.testEmail')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSendPreview('push')}
              disabled={sendingPreview || !settings.push_enabled}
            >
              <Smartphone className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('notifications.testPush')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSendPreview('in_app')}
              disabled={sendingPreview || !settings.in_app_enabled}
            >
              <Monitor className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('notifications.testInApp')}
            </Button>
          </div>
        </SettingsRow>
      </SettingsPanel>

      {settings.unsubscribe_token ? (
        <SettingsPanel
          title={t('notifications.unsubscribe')}
          description={t('notifications.unsubscribeDesc')}
        >
          <SettingsRow label={t('notifications.unsubscribeLinkText')}>
            <MonoAnnotation className="text-foreground">
              /unsubscribe/{settings.unsubscribe_token}
            </MonoAnnotation>
            {settings.unsubscribed_at ? (
              <MonoAnnotation tone="destructive" className="mt-1 block">
                {t('notifications.unsubscribedOn', {
                  date: new Date(settings.unsubscribed_at).toLocaleDateString(),
                })}
              </MonoAnnotation>
            ) : null}
          </SettingsRow>
        </SettingsPanel>
      ) : null}

      <div className="flex items-center justify-end gap-4">
        {success ? <MonoAnnotation tone="success">{success}</MonoAnnotation> : null}
        {error ? <MonoAnnotation tone="destructive">{error}</MonoAnnotation> : null}
        <Button onClick={handleSave} disabled={saving}>
          {saving ? t('notifications.saving') : t('notifications.savePreferences')}
        </Button>
      </div>
    </div>
  );
}
