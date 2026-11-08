"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const USER_EMAIL_STORAGE_KEY = "userEmail";

function isValidEmail(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) return false;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed);
}

export function IdentitySettings({ onChange }: { onChange?: (userEmail: string | null) => void }) {
  const [email, setEmail] = useState(() => {
    if (typeof window === "undefined") return "";
    return window.localStorage.getItem(USER_EMAIL_STORAGE_KEY) || "";
  });
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const normalized = useMemo(() => email.trim(), [email]);
  const valid = useMemo(() => (normalized ? isValidEmail(normalized) : true), [normalized]);

  const handleSave = () => {
    setError(null);
    setSaved(null);

    if (normalized && !isValidEmail(normalized)) {
      setError("Please enter a valid email address.");
      return;
    }

    if (!normalized) {
      window.localStorage.removeItem(USER_EMAIL_STORAGE_KEY);
      setSaved("Email cleared.");
      onChange?.(null);
      return;
    }

    window.localStorage.setItem(USER_EMAIL_STORAGE_KEY, normalized);
    setSaved("Email saved.");
    onChange?.(normalized);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Identity</CardTitle>
        <CardDescription>
          Set the email address used to scope settings (notifications and default model) for API requests.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2">
          <Label htmlFor="settings_user_email">Email</Label>
          <Input
            id="settings_user_email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            aria-invalid={!valid}
          />
          <div className="text-xs text-muted-foreground">
            Stored locally in your browser and sent as <span className="font-mono">X-User-Email</span>.
          </div>
        </div>

        <div className="flex items-center justify-end gap-4">
          {saved && <span className="text-success text-sm">{saved}</span>}
          {error && <span className="text-destructive text-sm">{error}</span>}
          <Button onClick={handleSave}>Save</Button>
        </div>
      </CardContent>
    </Card>
  );
}
