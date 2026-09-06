'use client';

import React, { useEffect, useState, useRef } from 'react';
import { User, Camera, Trash2, Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
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
      <div className="rounded-md border border-dashed bg-muted/30 p-4 text-muted-foreground">
        {t('profile.loadingProfile')}
      </div>
    );
  }

  if (!userEmail) {
    return (
      <div className="rounded-md border border-dashed bg-muted/30 p-4 text-muted-foreground">
        {t('emailRequired')}
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex items-center gap-3 rounded-md border border-destructive/20 bg-destructive/5 p-4 text-destructive">
        <span className="flex-1">{error || t('profile.somethingWentWrong')}</span>
        <Button onClick={fetchProfile} variant="outline" size="sm">
          {t('profile.retry')}
        </Button>
      </div>
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

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
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
    <div className="grid gap-6">
      {/* Avatar Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Camera className="h-5 w-5 text-primary" aria-hidden="true" />
            <CardTitle>{t('profile.profilePicture')}</CardTitle>
          </div>
          <CardDescription>{t('profile.profilePictureDesc')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6">
            <div className="relative">
              {profile.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt={t('profile.profile')}
                  className="h-24 w-24 rounded-full object-cover border-2 border-muted"
                />
              ) : (
                <div className="h-24 w-24 rounded-full bg-muted flex items-center justify-center border-2 border-muted">
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
              {profile.avatar_url && (
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
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Profile Information Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="h-5 w-5 text-primary" aria-hidden="true" />
            <CardTitle>{t('profile.profileInformation')}</CardTitle>
          </div>
          <CardDescription>{t('profile.profileInformationDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="email">{t('profile.email')}</Label>
            <Input id="email" type="email" value={profile.email} disabled className="bg-muted" />
            <span className="text-xs text-muted-foreground">{t('profile.emailCannotChange')}</span>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="full_name">{t('profile.fullName')}</Label>
            <Input
              id="full_name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder={t('profile.fullNamePlaceholder')}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="phone">{t('profile.phone')}</Label>
            <Input
              id="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 234 567 8900"
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="bio">{t('profile.bio')}</Label>
            <textarea
              id="bio"
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder={t('profile.bioPlaceholder')}
              rows={3}
              maxLength={500}
            />
            <span className="text-xs text-muted-foreground">
              {t('profile.charactersCount', { count: bio.length, max: 500 })}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Preferences Card */}
      <Card>
        <CardHeader>
          <CardTitle>{t('profile.preferences')}</CardTitle>
          <CardDescription>{t('profile.preferencesDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="timezone">{t('profile.timezone')}</Label>
            <select
              id="timezone"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
            >
              {TIMEZONES.map((tz) => (
                <option key={tz.value} value={tz.value}>
                  {tz.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="language">{t('profile.language')}</Label>
            <select
              id="language"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              {LANGUAGES.map((lang) => (
                <option key={lang.value} value={lang.value}>
                  {lang.label}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Account Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>{t('profile.accountInformation')}</CardTitle>
          <CardDescription>{t('profile.accountInformationDesc')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">{t('profile.role')}:</span>
              <span className="ml-2 capitalize">{profile.role}</span>
            </div>
            <div>
              <span className="text-muted-foreground">{t('profile.status')}:</span>
              <span className={`ml-2 ${profile.is_active ? 'text-green-600' : 'text-red-600'}`}>
                {profile.is_active ? t('profile.active') : t('profile.inactive')}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">{t('profile.verified')}:</span>
              <span
                className={`ml-2 ${profile.is_verified ? 'text-green-600' : 'text-yellow-600'}`}
              >
                {profile.is_verified ? t('profile.yes') : t('profile.pending')}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">{t('profile.memberSince')}:</span>
              <span className="ml-2">
                {profile.created_at
                  ? new Date(profile.created_at).toLocaleDateString()
                  : t('profile.na')}
              </span>
            </div>
            {profile.last_login_at && (
              <div className="col-span-2">
                <span className="text-muted-foreground">{t('profile.lastLogin')}:</span>
                <span className="ml-2">{new Date(profile.last_login_at).toLocaleString()}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex items-center justify-end gap-4">
        {success && <span className="text-green-600 text-sm">{success}</span>}
        {error && <span className="text-red-600 text-sm">{error}</span>}
        <Button onClick={handleSave} disabled={saving}>
          {saving ? t('profile.saving') : t('profile.saveProfile')}
        </Button>
      </div>
    </div>
  );
}
