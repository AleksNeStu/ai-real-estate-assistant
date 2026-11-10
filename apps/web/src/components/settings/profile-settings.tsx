'use client';

import { useEffect, useState, useRef, type ChangeEvent } from 'react';
import { User, Camera, Trash2, Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { MonoAnnotation } from '../ui/mono-annotation';
import { SettingsPanel, SettingsRow } from './settings-panel';
import { getProfile, updateProfile, uploadAvatar, deleteAvatar } from '@/lib/api';
import { ProfileResponse, ProfileUpdate } from '@/lib/types';

// Common timezones
const TIMEZONES = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
  { value: 'Europe/London', label: 'London (GMT/BST)' },
  { value: 'Europe/Berlin', label: 'Berlin (CET/CEST)' },
  { value: 'Europe/Warsaw', label: 'Warsaw (CET/CEST)' },
  { value: 'Europe/Moscow', label: 'Moscow (MSK)' },
  { value: 'America/New_York', label: 'New York (EST/EDT)' },
  { value: 'America/Chicago', label: 'Chicago (CST/CDT)' },
  { value: 'America/Denver', label: 'Denver (MST/MDT)' },
  { value: 'America/Los_Angeles', label: 'Los Angeles (PST/PDT)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Asia/Shanghai', label: 'Shanghai (CST)' },
  { value: 'Asia/Dubai', label: 'Dubai (GST)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEST/AEDT)' },
];

// Supported languages
const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'de', label: 'Deutsch' },
  { value: 'pl', label: 'Polski' },
  { value: 'ru', label: 'Русский' },
  { value: 'es', label: 'Español' },
  { value: 'fr', label: 'Français' },
];

/**
 * The profile.
 *
 * What a visitor sees about the person is a list of fields, so it is a
 * ledger: one rule opens it and every row is a field with the label that
 * says what it is. The picture is the one thing that is an object, so it
 * keeps a card.
 */
export function ProfileSettings({ userEmail }: { userEmail: string | null }) {
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const t = useTranslations('settings');

  // Form state
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [bio, setBio] = useState('');
  const [timezone, setTimezone] = useState('UTC');
  const [language, setLanguage] = useState('en');

  useEffect(() => {
    if (!userEmail) {
      setLoading(false);
      return;
    }
    fetchProfile();
  }, [userEmail]);

  const fetchProfile = async () => {
    try {
      const data = await getProfile();
      setProfile(data);
      setFullName(data.full_name || '');
      setPhone(data.phone || '');
      setBio(data.bio || '');
      setTimezone(data.timezone || 'UTC');
      setLanguage(data.language || 'en');
      setError(null);
    } catch {
      setError(t('profile.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <SettingsPanel title={t('profile.profile')} description={t('profile.loadingProfile')}>
        <div />
      </SettingsPanel>
    );
  }

  if (!userEmail) {
    return (
      <SettingsPanel title={t('profile.profile')} description={t('emailRequired')}>
        <div />
      </SettingsPanel>
    );
  }

  if (!profile) {
    return (
      <SettingsPanel
        title={t('profile.profile')}
        description={error || t('profile.somethingWentWrong')}
      >
        <div className="flex items-center gap-3 py-4">
          <Button onClick={fetchProfile} variant="outline" size="sm">
            {t('profile.retry')}
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
      const updateData: ProfileUpdate = {
        full_name: fullName || undefined,
        phone: phone || undefined,
        bio: bio || undefined,
        timezone,
        language,
      };
      const updated = await updateProfile(updateData);
      setProfile(updated);
      setSuccess(t('saved'));
    } catch {
      setError(t('error'));
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/png', 'image/jpeg', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      setError(t('profile.invalidFileType'));
      return;
    }

    // Validate file size (2MB max)
    if (file.size > 2 * 1024 * 1024) {
      setError(t('profile.fileTooLarge'));
      return;
    }

    setUploadingAvatar(true);
    setError(null);

    try {
      const result = await uploadAvatar(file);
      setProfile({ ...profile, avatar_url: result.avatar_url });
      setSuccess(t('profile.avatarUploaded'));
    } catch {
      setError(t('profile.avatarUploadFailed'));
    } finally {
      setUploadingAvatar(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteAvatar = async () => {
    setUploadingAvatar(true);
    setError(null);

    try {
      await deleteAvatar();
      setProfile({ ...profile, avatar_url: null });
      setSuccess(t('profile.avatarDeleted'));
    } catch {
      setError(t('profile.avatarDeleteFailed'));
    } finally {
      setUploadingAvatar(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      {/* The picture is an object, so it keeps a card. */}
      <div className="rounded-lg border border-border bg-card p-4">
        <div className="mb-3 flex items-center gap-2">
          <Camera className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <span className="text-app font-medium text-foreground">
            {t('profile.profilePicture')}
          </span>
        </div>
        <div className="flex items-center gap-6">
          <div className="relative">
            {profile.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt={t('profile.profile')}
                className="h-24 w-24 rounded-full border-2 border-muted object-cover"
              />
            ) : (
              <div className="flex h-24 w-24 items-center justify-center rounded-full border-2 border-muted bg-muted">
                <User className="h-12 w-12 text-muted-foreground" aria-hidden="true" />
              </div>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <input
              type="file"
              ref={fileInputRef}
              accept="image/png,image/jpeg,image/webp"
              onChange={handleAvatarUpload}
              className="hidden"
              id="avatar-upload"
            />
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingAvatar}
            >
              {uploadingAvatar ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Camera className="mr-2 h-4 w-4" aria-hidden="true" />
              )}
              {uploadingAvatar ? t('profile.uploading') : t('profile.uploadPhoto')}
            </Button>
            {profile.avatar_url ? (
              <Button
                variant="outline"
                size="sm"
                onClick={handleDeleteAvatar}
                disabled={uploadingAvatar}
                className="text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('profile.remove')}
              </Button>
            ) : null}
          </div>
        </div>
      </div>

      <SettingsPanel
        title={t('profile.profileInformation')}
        description={t('profile.profileInformationDesc')}
      >
        <SettingsRow
          label={t('profile.email')}
          description={t('profile.emailCannotChange')}
        >
          <Input id="email" type="email" value={profile.email} disabled className="bg-muted max-w-[360px]" />
        </SettingsRow>

        <SettingsRow label={t('profile.fullName')}>
          <Input
            id="full_name"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder={t('profile.fullNamePlaceholder')}
            className="max-w-[360px]"
          />
        </SettingsRow>

        <SettingsRow label={t('profile.phone')}>
          <Input
            id="phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+1 234 567 8900"
            className="max-w-[360px]"
          />
        </SettingsRow>

        <SettingsRow label={t('profile.bio')} description={t('profile.charactersCount', { count: bio.length, max: 500 })}>
          <textarea
            id="bio"
            className="flex min-h-[80px] max-w-[480px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder={t('profile.bioPlaceholder')}
            rows={3}
            maxLength={500}
          />
        </SettingsRow>
      </SettingsPanel>

      <SettingsPanel title={t('profile.preferences')} description={t('profile.preferencesDesc')}>
        <SettingsRow label={t('profile.timezone')}>
          <select
            id="timezone"
            className="h-8 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
          >
            {TIMEZONES.map((tz) => (
              <option key={tz.value} value={tz.value}>
                {tz.label}
              </option>
            ))}
          </select>
        </SettingsRow>

        <SettingsRow label={t('profile.language')}>
          <select
            id="language"
            className="h-8 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.value} value={lang.value}>
                {lang.label}
              </option>
            ))}
          </select>
        </SettingsRow>
      </SettingsPanel>

      <SettingsPanel
        title={t('profile.accountInformation')}
        description={t('profile.accountInformationDesc')}
      >
        <SettingsRow label={t('profile.role')}>
          <span className="text-app capitalize text-foreground">{profile.role}</span>
        </SettingsRow>
        <SettingsRow label={t('profile.status')}>
          <MonoAnnotation tone={profile.is_active ? 'success' : 'destructive'}>
            {profile.is_active ? t('profile.active') : t('profile.inactive')}
          </MonoAnnotation>
        </SettingsRow>
        <SettingsRow label={t('profile.verified')}>
          <MonoAnnotation tone={profile.is_verified ? 'success' : 'warning'}>
            {profile.is_verified ? t('profile.yes') : t('profile.pending')}
          </MonoAnnotation>
        </SettingsRow>
        <SettingsRow label={t('profile.memberSince')}>
          <MonoAnnotation>
            {profile.created_at
              ? new Date(profile.created_at).toLocaleDateString()
              : t('profile.na')}
          </MonoAnnotation>
        </SettingsRow>
        {profile.last_login_at ? (
          <SettingsRow label={t('profile.lastLogin')}>
            <MonoAnnotation>{new Date(profile.last_login_at).toLocaleString()}</MonoAnnotation>
          </SettingsRow>
        ) : null}
      </SettingsPanel>

      <div className="flex items-center justify-end gap-4">
        {success ? <MonoAnnotation tone="success">{success}</MonoAnnotation> : null}
        {error ? <MonoAnnotation tone="destructive">{error}</MonoAnnotation> : null}
        <Button onClick={handleSave} disabled={saving}>
          {saving ? t('profile.saving') : t('profile.saveProfile')}
        </Button>
      </div>
    </div>
  );
}
