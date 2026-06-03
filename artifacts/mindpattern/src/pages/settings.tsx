import { useEffect, useState } from "react";
import { userService } from "@/services/userService";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import type { UserSettingsResponse } from "@/types";

export default function Settings() {
  const [settings, setSettings] = useState<UserSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    userService
      .getSettings()
      .then(setSettings)
      .catch(() => setLoadError("Failed to load settings."))
      .finally(() => setLoading(false));
  }, []);

  const showToast = (type: "success" | "error", text: string) => {
    setToastMsg({ type, text });
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleToggle = async (
    key: "ai_analysis_enabled" | "weekly_summary_enabled",
    value: boolean
  ) => {
    if (!settings) return;
    setSaving(key);
    const optimistic = { ...settings, [key]: value };
    setSettings(optimistic);
    try {
      const updated = await userService.updateSettings({ [key]: value });
      setSettings(updated);
      showToast("success", "Settings saved.");
    } catch {
      setSettings(settings);
      showToast("error", "Failed to save settings. Please try again.");
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto w-full space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-3xl font-serif text-foreground">Settings</h2>
        <p className="text-muted-foreground mt-2">Manage your account preferences.</p>
      </div>

      {toastMsg && (
        <div
          className={`flex items-center gap-2 text-sm rounded-lg px-4 py-3 border ${
            toastMsg.type === "success"
              ? "bg-green-50 border-green-200 text-green-800"
              : "bg-destructive/10 border-destructive/30 text-destructive"
          }`}
          data-testid="settings-toast"
        >
          {toastMsg.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0" />
          )}
          {toastMsg.text}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin" />
          Loading settings…
        </div>
      ) : loadError ? (
        <p className="text-sm text-destructive">{loadError}</p>
      ) : settings ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Analysis & Notifications</CardTitle>
            <CardDescription>Control how MindPattern processes and shares your data.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <ToggleRow
              id="ai-analysis"
              label="AI Analysis"
              description="Allow MindPattern to analyze your entries for patterns and insights."
              checked={settings.ai_analysis_enabled}
              loading={saving === "ai_analysis_enabled"}
              onCheckedChange={(v) => handleToggle("ai_analysis_enabled", v)}
              testId="toggle-ai-analysis"
            />
            <ToggleRow
              id="weekly-summary"
              label="Weekly Summary"
              description="Receive a weekly digest of your mood, sleep, and stress trends."
              checked={settings.weekly_summary_enabled}
              loading={saving === "weekly_summary_enabled"}
              onCheckedChange={(v) => handleToggle("weekly_summary_enabled", v)}
              testId="toggle-weekly-summary"
            />
          </CardContent>
        </Card>
      ) : null}

      {settings && (
        <Card className="bg-muted/40">
          <CardContent className="pt-5">
            <p className="text-sm text-muted-foreground">
              Signed in as <span className="font-medium text-foreground">{settings.email}</span>
              {settings.display_name ? ` · ${settings.display_name}` : ""}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ToggleRow({
  id,
  label,
  description,
  checked,
  loading,
  onCheckedChange,
  testId,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  loading: boolean;
  onCheckedChange: (v: boolean) => void;
  testId?: string;
}) {
  return (
    <div className="flex items-start gap-4">
      <div className="flex-1">
        <Label htmlFor={id} className="text-sm font-medium cursor-pointer">
          {label}
        </Label>
        <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
      </div>
      <div className="flex items-center gap-2 pt-0.5">
        {loading && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
        <Switch
          id={id}
          checked={checked}
          onCheckedChange={onCheckedChange}
          disabled={loading}
          data-testid={testId}
        />
      </div>
    </div>
  );
}
