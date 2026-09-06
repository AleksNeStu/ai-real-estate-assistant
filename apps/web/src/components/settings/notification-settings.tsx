'use client';

import React, { useEffect, useState } from 'react';
import { Bell, Smartphone, Mail, Monitor, Clock, Send } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Label } from '../ui/label';
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
      <div className="rounded-md border border-dashed bg-muted/30 p-4 text-muted-foreground">
        {t('emailRequired')}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rounded-md border border-dashed bg-muted/30 p-4 text-muted-foreground">
        {t('notifications.loadingSettings')}
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="flex items-center gap-3 rounded-md border border-destructive/20 bg-destructive/5 p-4 text-destructive">
        <span className="flex-1">{error || t('notifications.somethingWentWrong')}</span>
        <Button onClick={fetchSettings} variant="outline" size="sm">
          {t('notifications.retry')}
        </Button>
      </div>
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
    <div className="grid gap-6">
      {/* Notification Types Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-primary" aria-hidden="true" />
            <CardTitle>{t('notifications.notificationTypes')}</CardTitle>
          </div>
          <CardDescription>{t('notifications.notificationTypesDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="price_alerts" className="flex flex-col space-y-1">
              <span>{t('notifications.priceAlerts')}</span>
              <span className="font-normal text-muted-foreground">
                {t('notifications.priceAlertsDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="price_alerts"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.price_alerts_enabled}
              onChange={() => toggleSetting('price_alerts_enabled')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="new_listings" className="flex flex-col space-y-1">
              <span>{t('notifications.newListings')}</span>
              <span className="font-normal text-muted-foreground">
                {t('notifications.newListingsDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="new_listings"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.new_listings_enabled}
              onChange={() => toggleSetting('new_listings_enabled')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="saved_search" className="flex flex-col space-y-1">
              <span>{t('notifications.savedSearchUpdates')}</span>
              <span className="font-normal text-muted-foreground">
                {t('notifications.savedSearchUpdatesDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="saved_search"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.saved_search_enabled}
              onChange={() => toggleSetting('saved_search_enabled')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="market_updates" className="flex flex-col space-y-1">
              <span>{t('notifications.marketUpdates')}</span>
              <span className="font-normal text-muted-foreground">
                {t('notifications.marketUpdatesDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="market_updates"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.market_updates_enabled}
              onChange={() => toggleSetting('market_updates_enabled')}
            />
          </div>
        </CardContent>
      </Card>

      {/* Notification Channels Card */}
      <Card>
        <CardHeader>
          <CardTitle>{t('notifications.channels')}</CardTitle>
          <CardDescription>{t('notifications.channelsDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="email_channel" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4" aria-hidden="true" />
                <span>{t('notifications.emailChannel')}</span>
              </div>
              <span className="font-normal text-muted-foreground">
                {t('notifications.emailChannelDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="email_channel"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.email_enabled}
              onChange={() => toggleSetting('email_enabled')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="push_channel" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <Smartphone className="h-4 w-4" aria-hidden="true" />
                <span>{t('notifications.pushChannel')}</span>
              </div>
              <span className="font-normal text-muted-foreground">
                {t('notifications.pushChannelDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="push_channel"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.push_enabled}
              onChange={() => toggleSetting('push_enabled')}
              disabled={pushPermissionStatus === 'denied'}
            />
          </div>

          {pushPermissionStatus === 'default' && settings.push_enabled && (
            <div className="rounded-md bg-muted p-3 text-sm">
              <p className="mb-2">{t('notifications.enablePushBrowser')}</p>
              <Button size="sm" onClick={handleEnablePush}>
                <Bell className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('notifications.enablePush')}
              </Button>
            </div>
          )}

          {pushPermissionStatus === 'denied' && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {t('notifications.pushBlocked')}
            </div>
          )}

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="in_app_channel" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <Monitor className="h-4 w-4" aria-hidden="true" />
                <span>{t('notifications.inAppChannel')}</span>
              </div>
              <span className="font-normal text-muted-foreground">
                {t('notifications.inAppChannelDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="in_app_channel"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.in_app_enabled}
              onChange={() => toggleSetting('in_app_enabled')}
            />
          </div>
        </CardContent>
      </Card>

      {/* Frequency & Digest Card */}
      <Card>
        <CardHeader>
          <CardTitle>{t('notifications.frequencyDigest')}</CardTitle>
          <CardDescription>{t('notifications.frequencyDigestDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="alert_frequency">{t('notifications.alertFrequency')}</Label>
            <select
              id="alert_frequency"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={settings.alert_frequency}
              onChange={(e) =>
                updateSetting('alert_frequency', e.target.value as 'instant' | 'daily' | 'weekly')
              }
            >
              <option value="instant">{t('notifications.instant')}</option>
              <option value="daily">{t('notifications.dailyDigest')}</option>
              <option value="weekly">{t('notifications.weeklyDigest')}</option>
            </select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="daily_digest_time">{t('notifications.dailyDigestTime')}</Label>
            <input
              type="time"
              id="daily_digest_time"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={settings.daily_digest_time}
              onChange={(e) => updateSetting('daily_digest_time', e.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="weekly_digest_day">{t('notifications.weeklyDigestDay')}</Label>
            <select
              id="weekly_digest_day"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={settings.weekly_digest_day}
              onChange={(e) => updateSetting('weekly_digest_day', e.target.value)}
            >
              {DAYS_OF_WEEK.map((day) => (
                <option key={day} value={day}>
                  {day.charAt(0).toUpperCase() + day.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Settings Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-primary" aria-hidden="true" />
            <CardTitle>{t('notifications.advancedSettings')}</CardTitle>
          </div>
          <CardDescription>{t('notifications.advancedSettingsDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="quiet_hours_start">{t('notifications.quietHoursStart')}</Label>
              <input
                type="time"
                id="quiet_hours_start"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={settings.quiet_hours_start || ''}
                onChange={(e) => updateSetting('quiet_hours_start', e.target.value || null)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="quiet_hours_end">{t('notifications.quietHoursEnd')}</Label>
              <input
                type="time"
                id="quiet_hours_end"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={settings.quiet_hours_end || ''}
                onChange={(e) => updateSetting('quiet_hours_end', e.target.value || null)}
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="price_drop_threshold">{t('notifications.priceDropThreshold')}</Label>
            <input
              type="number"
              id="price_drop_threshold"
              min="1"
              max="50"
              step="0.5"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={settings.price_drop_threshold}
              onChange={(e) => updateSetting('price_drop_threshold', parseFloat(e.target.value))}
            />
            <span className="text-xs text-muted-foreground">
              {t('notifications.priceDropThresholdDesc')}
            </span>
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="expert_mode" className="flex flex-col space-y-1">
              <span>{t('notifications.expertMode')}</span>
              <span className="font-normal text-muted-foreground">
                {t('notifications.expertModeDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="expert_mode"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.expert_mode}
              onChange={() => toggleSetting('expert_mode')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="marketing_emails" className="flex flex-col space-y-1">
              <span>{t('notifications.productUpdates')}</span>
              <span className="font-normal text-muted-foreground">
                {t('notifications.productUpdatesDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="marketing_emails"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.marketing_emails}
              onChange={() => toggleSetting('marketing_emails')}
            />
          </div>
        </CardContent>
      </Card>

      {/* Test Notifications Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Send className="h-5 w-5 text-primary" aria-hidden="true" />
            <CardTitle>{t('notifications.testNotifications')}</CardTitle>
          </div>
          <CardDescription>{t('notifications.testNotificationsDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
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
        </CardContent>
      </Card>

      {/* Unsubscribe Info */}
      {settings.unsubscribe_token && (
        <Card>
          <CardHeader>
            <CardTitle>{t('notifications.unsubscribe')}</CardTitle>
            <CardDescription>{t('notifications.unsubscribeDesc')}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {t('notifications.unsubscribeLinkText')}{' '}
              <code className="text-xs bg-muted px-1 py-0.5 rounded">
                /unsubscribe/{settings.unsubscribe_token}
              </code>
            </p>
            {settings.unsubscribed_at && (
              <p className="mt-2 text-sm text-destructive">
                {t('notifications.unsubscribedOn', {
                  date: new Date(settings.unsubscribed_at).toLocaleDateString(),
                })}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Save Button */}
      <div className="flex items-center justify-end gap-4">
        {success && <span className="text-green-600 text-sm">{success}</span>}
        {error && <span className="text-red-600 text-sm">{error}</span>}
        <Button onClick={handleSave} disabled={saving}>
          {saving ? t('notifications.saving') : t('notifications.savePreferences')}
        </Button>
      </div>
    </div>
  );
}
