'use client';

import { useEffect, useState } from 'react';
import { Download, Loader2, Mail, Phone, MessageSquare, Clock } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { MonoAnnotation } from '../ui/mono-annotation';
import { SettingsPanel, SettingsRow } from './settings-panel';
import { getProfile, updatePrivacySettings, requestDataExport, getExportStatus } from '@/lib/api';
import {
  ProfileResponse,
  PrivacySettings as PrivacySettingsType,
  DataExportRequest,
  DataExportStatusResponse,
} from '@/lib/types';

/**
 * The data on this deployment.
 *
 * What is visible and what is kept are two lists of switches, so they are
 * ledgers: one rule opens each and every row is a switch with the label
 * that says what it is. The export is a job, so it carries its progress.
 */
export function PrivacySettings({ userEmail }: { userEmail: string | null }) {
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const t = useTranslations('settings');

  // Privacy settings state
  const [settings, setSettings] = useState<PrivacySettingsType>({
    profile_visible: true,
    activity_visible: false,
    show_email: false,
    show_phone: false,
    allow_contact: true,
  });

  // Export state
  const [exporting, setExporting] = useState(false);
  const [exportJob, setExportJob] = useState<DataExportStatusResponse | null>(null);
  const [pollingExport, setPollingExport] = useState(false);

  useEffect(() => {
    if (!userEmail) {
      setLoading(false);
      return;
    }
    fetchProfile();
  }, [userEmail]);

  // Poll export status when job is processing
  useEffect(() => {
    if (
      !pollingExport ||
      !exportJob ||
      exportJob.status === 'completed' ||
      exportJob.status === 'failed'
    ) {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const status = await getExportStatus(exportJob.export_id);
        setExportJob(status);

        if (status.status === 'completed' || status.status === 'failed') {
          setPollingExport(false);
        }
      } catch {
        setPollingExport(false);
        setError(t('privacy.exportStatusFailed'));
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [pollingExport, exportJob]);

  const fetchProfile = async () => {
    try {
      const data = await getProfile();
      setProfile(data);
      if (data.privacy_settings) {
        setSettings({
          profile_visible: data.privacy_settings.profile_visible ?? true,
          activity_visible: data.privacy_settings.activity_visible ?? false,
          show_email: data.privacy_settings.show_email ?? false,
          show_phone: data.privacy_settings.show_phone ?? false,
          allow_contact: data.privacy_settings.allow_contact ?? true,
        });
      }
      setError(null);
    } catch {
      setError(t('privacy.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  if (!userEmail) {
    return (
      <SettingsPanel title={t('privacy.privacyControls')} description={t('emailRequired')}>
        <div />
      </SettingsPanel>
    );
  }

  if (loading) {
    return (
      <SettingsPanel
        title={t('privacy.privacyControls')}
        description={t('privacy.loadingPrivacy')}
      >
        <div />
      </SettingsPanel>
    );
  }

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const updated = await updatePrivacySettings(settings);
      setProfile(updated);
      setSuccess(t('saved'));
    } catch {
      setError(t('error'));
    } finally {
      setSaving(false);
    }
  };

  const toggleSetting = (key: keyof PrivacySettingsType) => {
    setSettings({ ...settings, [key]: !settings[key] });
  };

  const handleExportData = async () => {
    setExporting(true);
    setError(null);
    setExportJob(null);

    try {
      const request: DataExportRequest = {
        format: 'json',
        include_favorites: true,
        include_search_history: true,
        include_documents: true,
      };
      const response = await requestDataExport(request);
      setExportJob({
        export_id: response.export_id,
        status: response.status,
        progress_percent: 0,
        download_url: null,
        expires_at: null,
        error_message: null,
        created_at: response.created_at,
        completed_at: null,
      });
      setPollingExport(true);
      setSuccess(t('privacy.exportStarted'));
    } catch {
      setError(t('privacy.exportStartFailed'));
    } finally {
      setExporting(false);
    }
  };

  const handleDownload = () => {
    if (exportJob?.download_url) {
      window.open(exportJob.download_url, '_blank');
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <SettingsPanel
        title={t('privacy.privacyControls')}
        description={t('privacy.privacyControlsDesc')}
      >
        <SettingsRow
          label={
            <Label htmlFor="profile_visible" className="flex cursor-pointer items-center gap-2">
              {t('privacy.publicProfile')}
            </Label>
          }
          description={t('privacy.publicProfileDesc')}
          action={
            <input
              type="checkbox"
              id="profile_visible"
              className="h-4 w-4 rounded border-border"
              checked={settings.profile_visible}
              onChange={() => toggleSetting('profile_visible')}
            />
          }
        />

        <SettingsRow
          label={
            <Label htmlFor="activity_visible" className="flex cursor-pointer items-center gap-2">
              {t('privacy.activityVisibility')}
            </Label>
          }
          description={t('privacy.activityVisibilityDesc')}
          action={
            <input
              type="checkbox"
              id="activity_visible"
              className="h-4 w-4 rounded border-border"
              checked={settings.activity_visible}
              onChange={() => toggleSetting('activity_visible')}
            />
          }
        />

        <SettingsRow
          label={
            <Label htmlFor="show_email" className="flex cursor-pointer items-center gap-2">
              <Mail className="h-4 w-4" aria-hidden="true" />
              {t('privacy.showEmail')}
            </Label>
          }
          description={t('privacy.showEmailDesc')}
          action={
            <input
              type="checkbox"
              id="show_email"
              className="h-4 w-4 rounded border-border"
              checked={settings.show_email}
              onChange={() => toggleSetting('show_email')}
            />
          }
        />

        <SettingsRow
          label={
            <Label htmlFor="show_phone" className="flex cursor-pointer items-center gap-2">
              <Phone className="h-4 w-4" aria-hidden="true" />
              {t('privacy.showPhone')}
            </Label>
          }
          description={t('privacy.showPhoneDesc')}
          action={
            <input
              type="checkbox"
              id="show_phone"
              className="h-4 w-4 rounded border-border"
              checked={settings.show_phone}
              onChange={() => toggleSetting('show_phone')}
            />
          }
        />

        <SettingsRow
          label={
            <Label htmlFor="allow_contact" className="flex cursor-pointer items-center gap-2">
              <MessageSquare className="h-4 w-4" aria-hidden="true" />
              {t('privacy.allowContact')}
            </Label>
          }
          description={t('privacy.allowContactDesc')}
          action={
            <input
              type="checkbox"
              id="allow_contact"
              className="h-4 w-4 rounded border-border"
              checked={settings.allow_contact}
              onChange={() => toggleSetting('allow_contact')}
            />
          }
        />
      </SettingsPanel>

      <SettingsPanel
        title={t('privacy.dataExportGdpr')}
        description={t('privacy.dataExportGdprDesc')}
      >
        <SettingsRow label={t('privacy.exportIncludes')}>
          <div className="flex flex-col gap-1 text-annot text-muted-foreground">
            <span>{t('privacy.exportProfileInfo')}</span>
            <span>{t('privacy.exportFavorites')}</span>
            <span>{t('privacy.exportSearchHistory')}</span>
            <span>{t('privacy.exportDocuments')}</span>
          </div>
        </SettingsRow>

        <SettingsRow label={t('privacy.exportProcessingInfo')}>
          <Button
            variant="outline"
            onClick={handleExportData}
            disabled={exporting || pollingExport}
          >
            {exporting || pollingExport ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Download className="mr-2 h-4 w-4" aria-hidden="true" />
            )}
            {exporting
              ? t('privacy.startingExport')
              : pollingExport
                ? t('privacy.processing')
                : t('privacy.requestDataExport')}
          </Button>
        </SettingsRow>

        {exportJob ? (
          <SettingsRow label={t('privacy.exportStatus')}>
            <div className="flex flex-col gap-2">
              <MonoAnnotation
                tone={
                  exportJob.status === 'completed'
                    ? 'success'
                    : exportJob.status === 'failed'
                      ? 'destructive'
                      : 'warning'
                }
              >
                {exportJob.status.charAt(0).toUpperCase() + exportJob.status.slice(1)}
              </MonoAnnotation>

              {exportJob.status === 'processing' ? (
                <div
                  className="h-2 w-full max-w-[320px] overflow-hidden rounded-full bg-muted-foreground/20"
                  role="progressbar"
                  aria-valuenow={exportJob.progress_percent}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={t('privacy.exportProgressLabel', {
                    percent: exportJob.progress_percent,
                  })}
                >
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${exportJob.progress_percent}%` }}
                  />
                </div>
              ) : null}

              {exportJob.status === 'completed' && exportJob.download_url ? (
                <Button onClick={handleDownload}>
                  <Download className="mr-2 h-4 w-4" aria-hidden="true" />
                  {t('privacy.downloadYourData')}
                </Button>
              ) : null}

              {exportJob.status === 'failed' && exportJob.error_message ? (
                <MonoAnnotation tone="destructive">{exportJob.error_message}</MonoAnnotation>
              ) : null}

              {exportJob.expires_at ? (
                <div className="flex items-center gap-1 text-annot text-muted-foreground">
                  <Clock className="h-3 w-3" aria-hidden="true" />
                  <span>
                    {t('privacy.linkExpires', {
                      date: new Date(exportJob.expires_at).toLocaleString(),
                    })}
                  </span>
                </div>
              ) : null}
            </div>
          </SettingsRow>
        ) : null}

        {profile?.gdpr_consent_at ? (
          <SettingsRow label={t('privacy.gdprConsentGiven', {
            date: new Date(profile.gdpr_consent_at).toLocaleDateString(),
          })}>
            <MonoAnnotation>{t('privacy.gdprConsentGiven', {
              date: new Date(profile.gdpr_consent_at).toLocaleDateString(),
            })}</MonoAnnotation>
          </SettingsRow>
        ) : null}
      </SettingsPanel>

      <div className="flex items-center justify-end gap-4">
        {success ? <MonoAnnotation tone="success">{success}</MonoAnnotation> : null}
        {error ? <MonoAnnotation tone="destructive">{error}</MonoAnnotation> : null}
        <Button onClick={handleSave} disabled={saving}>
          {saving ? t('privacy.saving') : t('privacy.savePrivacySettings')}
        </Button>
      </div>
    </div>
  );
}
