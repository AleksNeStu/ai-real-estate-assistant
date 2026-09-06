'use client';

import React, { useEffect, useState } from 'react';
import {
  Shield,
  Download,
  Loader2,
  Eye,
  EyeOff,
  Mail,
  Phone,
  MessageSquare,
  FileText,
  Clock,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Label } from '../ui/label';
import { getProfile, updatePrivacySettings, requestDataExport, getExportStatus } from '@/lib/api';
import {
  ProfileResponse,
  PrivacySettings as PrivacySettingsType,
  DataExportRequest,
  DataExportStatusResponse,
} from '@/lib/types';

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
      <div className="rounded-md border border-dashed bg-muted/30 p-4 text-muted-foreground">
        {t('emailRequired')}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rounded-md border border-dashed bg-muted/30 p-4 text-muted-foreground">
        {t('privacy.loadingPrivacy')}
      </div>
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
    <div className="grid gap-6">
      {/* Privacy Controls Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" aria-hidden="true" />
            <CardTitle>{t('privacy.privacyControls')}</CardTitle>
          </div>
          <CardDescription>{t('privacy.privacyControlsDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="profile_visible" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                {settings.profile_visible ? (
                  <Eye className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <EyeOff className="h-4 w-4" aria-hidden="true" />
                )}
                <span>{t('privacy.publicProfile')}</span>
              </div>
              <span className="font-normal text-muted-foreground">
                {t('privacy.publicProfileDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="profile_visible"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.profile_visible}
              onChange={() => toggleSetting('profile_visible')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="activity_visible" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                {settings.activity_visible ? (
                  <Eye className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <EyeOff className="h-4 w-4" aria-hidden="true" />
                )}
                <span>{t('privacy.activityVisibility')}</span>
              </div>
              <span className="font-normal text-muted-foreground">
                {t('privacy.activityVisibilityDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="activity_visible"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.activity_visible}
              onChange={() => toggleSetting('activity_visible')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="show_email" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4" aria-hidden="true" />
                <span>{t('privacy.showEmail')}</span>
              </div>
              <span className="font-normal text-muted-foreground">
                {t('privacy.showEmailDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="show_email"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.show_email}
              onChange={() => toggleSetting('show_email')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="show_phone" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4" aria-hidden="true" />
                <span>{t('privacy.showPhone')}</span>
              </div>
              <span className="font-normal text-muted-foreground">
                {t('privacy.showPhoneDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="show_phone"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.show_phone}
              onChange={() => toggleSetting('show_phone')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="allow_contact" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4" aria-hidden="true" />
                <span>{t('privacy.allowContact')}</span>
              </div>
              <span className="font-normal text-muted-foreground">
                {t('privacy.allowContactDesc')}
              </span>
            </Label>
            <input
              type="checkbox"
              id="allow_contact"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.allow_contact}
              onChange={() => toggleSetting('allow_contact')}
            />
          </div>
        </CardContent>
      </Card>

      {/* GDPR Data Export Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" aria-hidden="true" />
            <CardTitle>{t('privacy.dataExportGdpr')}</CardTitle>
          </div>
          <CardDescription>{t('privacy.dataExportGdprDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-sm text-muted-foreground">
            <p className="mb-2">{t('privacy.exportIncludes')}</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>{t('privacy.exportProfileInfo')}</li>
              <li>{t('privacy.exportFavorites')}</li>
              <li>{t('privacy.exportSearchHistory')}</li>
              <li>{t('privacy.exportDocuments')}</li>
            </ul>
            <p className="mt-2">{t('privacy.exportProcessingInfo')}</p>
          </div>

          {/* Export Status */}
          {exportJob && (
            <div className="rounded-md bg-muted p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{t('privacy.exportStatus')}</span>
                <span
                  className={`text-sm ${
                    exportJob.status === 'completed'
                      ? 'text-green-600'
                      : exportJob.status === 'failed'
                        ? 'text-red-600'
                        : 'text-yellow-600'
                  }`}
                >
                  {exportJob.status.charAt(0).toUpperCase() + exportJob.status.slice(1)}
                </span>
              </div>

              {exportJob.status === 'processing' && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{t('privacy.progress')}</span>
                    <span>{exportJob.progress_percent}%</span>
                  </div>
                  <div
                    className="h-2 bg-muted-foreground/20 rounded-full overflow-hidden"
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
                </div>
              )}

              {exportJob.status === 'completed' && exportJob.download_url && (
                <Button onClick={handleDownload} className="w-full">
                  <Download className="mr-2 h-4 w-4" aria-hidden="true" />
                  {t('privacy.downloadYourData')}
                </Button>
              )}

              {exportJob.status === 'failed' && exportJob.error_message && (
                <p className="text-sm text-red-600">{exportJob.error_message}</p>
              )}

              {exportJob.expires_at && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" aria-hidden="true" />
                  <span>
                    {t('privacy.linkExpires', {
                      date: new Date(exportJob.expires_at).toLocaleString(),
                    })}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Export Button */}
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

          {profile?.gdpr_consent_at && (
            <p className="text-xs text-muted-foreground">
              {t('privacy.gdprConsentGiven', {
                date: new Date(profile.gdpr_consent_at).toLocaleDateString(),
              })}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex items-center justify-end gap-4">
        {success && <span className="text-green-600 text-sm">{success}</span>}
        {error && <span className="text-red-600 text-sm">{error}</span>}
        <Button onClick={handleSave} disabled={saving}>
          {saving ? t('privacy.saving') : t('privacy.savePrivacySettings')}
        </Button>
      </div>
    </div>
  );
}
