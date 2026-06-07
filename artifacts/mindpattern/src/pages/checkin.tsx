import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { checkInService } from "@/services/checkInService";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, Pencil, Clock, Dumbbell, Users } from "lucide-react";
import { format, parseISO } from "date-fns";
import type { CheckInResponse } from "@/types";

const MOOD_LABELS: Record<number, string> = { 1: "Terrible", 2: "Poor", 3: "Okay", 4: "Good", 5: "Excellent" };
const MOOD_COLORS: Record<number, string> = {
  1: "bg-red-100 text-red-700 border-red-200",
  2: "bg-orange-100 text-orange-700 border-orange-200",
  3: "bg-yellow-100 text-yellow-700 border-yellow-200",
  4: "bg-green-100 text-green-700 border-green-200",
  5: "bg-emerald-100 text-emerald-700 border-emerald-200",
};

export default function CheckInPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();

  const [mood, setMood] = useState(3);
  const [stress, setStress] = useState(3);
  const [sleep, setSleep] = useState(7);
  const [energy, setEnergy] = useState(3);
  const [workload, setWorkload] = useState(3);
  const [exercised, setExercised] = useState(false);
  const [socialized, setSocialized] = useState(false);
  const [notes, setNotes] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [formReady, setFormReady] = useState(false);

  const { data: todayEntry, isLoading: checkingToday } = useQuery({
    queryKey: ["checkin-today"],
    queryFn: checkInService.getToday,
    retry: false,
  });

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ["checkins-history"],
    queryFn: () => checkInService.list(60),
  });

  useEffect(() => {
    if (checkingToday) return;
    if (todayEntry) {
      setMood(todayEntry.mood_rating);
      setStress(todayEntry.stress_level);
      setSleep(todayEntry.sleep_hours);
      setEnergy(todayEntry.energy_level ?? 3);
      setWorkload(todayEntry.workload_level ?? 3);
      setExercised(todayEntry.exercised);
      setSocialized(todayEntry.socialized);
      setNotes(todayEntry.notes ?? "");
    }
    setFormReady(true);
  }, [checkingToday, todayEntry]);

  const invalidateDashboard = () => {
    queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    queryClient.invalidateQueries({ queryKey: ["mood-trends"] });
    queryClient.invalidateQueries({ queryKey: ["stress-trends"] });
    queryClient.invalidateQueries({ queryKey: ["sleep-mood"] });
    queryClient.invalidateQueries({ queryKey: ["checkin-today"] });
    queryClient.invalidateQueries({ queryKey: ["checkins-history"] });
  };

  const createMutation = useMutation({
    mutationFn: checkInService.create,
    onSuccess: () => { invalidateDashboard(); setSuccess(true); setTimeout(() => setLocation("/dashboard"), 1500); },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to save check-in. Please try again.");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof checkInService.update>[1] }) =>
      checkInService.update(id, data),
    onSuccess: () => { invalidateDashboard(); setSuccess(true); setTimeout(() => setLocation("/dashboard"), 1500); },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to update check-in. Please try again.");
    },
  });

  const isPending = createMutation.isPending || updateMutation.isPending;
  const isEditMode = !!todayEntry;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const payload = {
      mood_rating: mood,
      stress_level: stress,
      sleep_hours: sleep,
      energy_level: energy,
      workload_level: workload,
      exercised,
      socialized,
      notes: notes.trim() || undefined,
    };
    if (isEditMode && todayEntry) {
      updateMutation.mutate({ id: todayEntry.id, data: payload });
    } else {
      createMutation.mutate({ ...payload, date: format(new Date(), "yyyy-MM-dd") });
    }
  };

  if (success) {
    return (
      <div className="p-8 max-w-2xl mx-auto w-full flex flex-col items-center justify-center gap-4 animate-in fade-in duration-300">
        <CheckCircle2 className="w-16 h-16 text-primary" />
        <h2 className="text-2xl font-serif text-foreground">
          {isEditMode ? "Check-in updated!" : "Check-in saved!"}
        </h2>
        <p className="text-muted-foreground">Redirecting to your dashboard…</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-2xl mx-auto w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-3xl font-serif text-foreground">Daily Check-in</h2>
          <p className="text-muted-foreground mt-2">
            {format(new Date(), "EEEE, MMMM d")}
          </p>
        </div>
        {isEditMode && (
          <div className="flex items-center gap-1.5 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-1.5 mt-1">
            <Pencil className="w-3.5 h-3.5" />
            Editing today's entry
          </div>
        )}
      </div>

      {checkingToday || !formReady ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-8">
              <SliderField
                label="Mood"
                value={mood}
                onChange={setMood}
                min={1} max={5} step={1}
                hint="1 = Terrible, 5 = Excellent"
                testId="input-mood"
              />
              <SliderField
                label="Stress"
                value={stress}
                onChange={setStress}
                min={1} max={5} step={1}
                hint="1 = Calm, 5 = Overwhelmed"
                testId="input-stress"
              />
              <SliderField
                label="Sleep"
                value={sleep}
                onChange={setSleep}
                min={0} max={24} step={0.5}
                unit="hrs"
                testId="input-sleep"
              />
              <SliderField
                label="Energy"
                value={energy}
                onChange={setEnergy}
                min={1} max={5} step={1}
                hint="1 = Drained, 5 = Full of energy"
                testId="input-energy"
              />
              <SliderField
                label="Workload"
                value={workload}
                onChange={setWorkload}
                min={1} max={5} step={1}
                hint="1 = Light, 5 = Very heavy"
                testId="input-workload"
              />

              <div className="flex items-center gap-8">
                <div className="flex items-center gap-2">
                  <Switch id="exercise" checked={exercised} onCheckedChange={setExercised} data-testid="input-exercised" />
                  <Label htmlFor="exercise">Exercised</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch id="social" checked={socialized} onCheckedChange={setSocialized} data-testid="input-socialized" />
                  <Label htmlFor="social">Socialized</Label>
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-base font-medium">Notes (optional)</Label>
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="How did you feel today? Any specific events?"
                  className="min-h-[100px]"
                  data-testid="input-notes"
                />
              </div>

              {error && (
                <p className="text-sm text-destructive" data-testid="error-message">{error}</p>
              )}

              <Button type="submit" disabled={isPending} className="w-full" data-testid="button-submit-checkin">
                {isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {isEditMode ? "Update Check-in" : "Save Check-in"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* History */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-muted-foreground" />
          <h3 className="text-base font-medium text-foreground">Past Check-ins</h3>
        </div>

        {historyLoading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 rounded-lg border bg-card animate-pulse" />
            ))}
          </div>
        ) : !history || history.length === 0 ? (
          <p className="text-sm text-muted-foreground">No past check-ins yet.</p>
        ) : (
          <div className="space-y-2">
            {history
              .filter((c) => c.date !== format(new Date(), "yyyy-MM-dd"))
              .map((entry) => (
                <HistoryRow key={entry.id} entry={entry} />
              ))}
          </div>
        )}
      </div>
    </div>
  );
}

function HistoryRow({ entry }: { entry: CheckInResponse }) {
  const moodColor = MOOD_COLORS[entry.mood_rating] ?? MOOD_COLORS[3];
  const moodLabel = MOOD_LABELS[entry.mood_rating] ?? "—";

  return (
    <div className="flex items-center gap-4 rounded-lg border bg-card px-4 py-3 text-sm">
      <span className="w-24 shrink-0 text-muted-foreground font-medium">
        {format(parseISO(entry.date), "MMM d, yyyy")}
      </span>

      <span className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium ${moodColor}`}>
        {moodLabel}
      </span>

      <div className="flex items-center gap-3 text-muted-foreground min-w-0 flex-wrap">
        <span title="Stress">😤 {entry.stress_level}/5</span>
        <span title="Sleep">😴 {entry.sleep_hours}h</span>
        <span title="Energy">⚡ {entry.energy_level ?? "—"}/5</span>
        {entry.exercised && (
          <Badge variant="secondary" className="gap-1 font-normal">
            <Dumbbell className="w-3 h-3" /> Exercise
          </Badge>
        )}
        {entry.socialized && (
          <Badge variant="secondary" className="gap-1 font-normal">
            <Users className="w-3 h-3" /> Social
          </Badge>
        )}
      </div>
    </div>
  );
}

function SliderField({
  label, value, onChange, min, max, step, unit, hint, testId,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  unit?: string;
  hint?: string;
  testId?: string;
}) {
  const display = unit ? `${value} ${unit}` : `${value}/${max}`;
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="text-base font-medium">{label} ({display})</Label>
        {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
      </div>
      <Slider
        value={[value]}
        onValueChange={(v) => onChange(v[0])}
        min={min} max={max} step={step}
        data-testid={testId}
      />
    </div>
  );
}
