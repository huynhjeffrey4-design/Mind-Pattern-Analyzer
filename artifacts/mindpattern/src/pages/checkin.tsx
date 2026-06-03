import { useState } from "react";
import { useLocation } from "wouter";
import { useQueryClient } from "@tanstack/react-query";
import { checkInService } from "@/services/checkInService";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Loader2, CheckCircle2 } from "lucide-react";
import { format } from "date-fns";

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

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await checkInService.create({
        date: format(new Date(), "yyyy-MM-dd"),
        mood_rating: mood,
        stress_level: stress,
        sleep_hours: sleep,
        energy_level: energy,
        workload_level: workload,
        exercised,
        socialized,
        notes: notes.trim() || undefined,
      });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      await queryClient.invalidateQueries({ queryKey: ["mood-trends"] });
      await queryClient.invalidateQueries({ queryKey: ["stress-trends"] });
      await queryClient.invalidateQueries({ queryKey: ["sleep-mood"] });
      setSuccess(true);
      setTimeout(() => setLocation("/dashboard"), 1500);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to save check-in. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="p-8 max-w-2xl mx-auto w-full flex flex-col items-center justify-center gap-4 animate-in fade-in duration-300">
        <CheckCircle2 className="w-16 h-16 text-primary" />
        <h2 className="text-2xl font-serif text-foreground">Check-in saved!</h2>
        <p className="text-muted-foreground">Redirecting to your dashboard…</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-2xl mx-auto w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h2 className="text-3xl font-serif text-foreground">Daily Check-in</h2>
        <p className="text-muted-foreground mt-2">Take a moment to reflect on your day.</p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-8">
            <SliderField
              label="Mood"
              value={mood}
              onChange={setMood}
              min={1}
              max={5}
              step={1}
              hint="1 = Terrible, 5 = Excellent"
              testId="input-mood"
            />

            <SliderField
              label="Stress"
              value={stress}
              onChange={setStress}
              min={1}
              max={5}
              step={1}
              hint="1 = Calm, 5 = Overwhelmed"
              testId="input-stress"
            />

            <SliderField
              label="Sleep"
              value={sleep}
              onChange={setSleep}
              min={0}
              max={24}
              step={0.5}
              unit="hrs"
              testId="input-sleep"
            />

            <SliderField
              label="Energy"
              value={energy}
              onChange={setEnergy}
              min={1}
              max={5}
              step={1}
              hint="1 = Drained, 5 = Full of energy"
              testId="input-energy"
            />

            <SliderField
              label="Workload"
              value={workload}
              onChange={setWorkload}
              min={1}
              max={5}
              step={1}
              hint="1 = Light, 5 = Very heavy"
              testId="input-workload"
            />

            <div className="flex items-center gap-8">
              <div className="flex items-center gap-2">
                <Switch
                  id="exercise"
                  checked={exercised}
                  onCheckedChange={setExercised}
                  data-testid="input-exercised"
                />
                <Label htmlFor="exercise">Exercised</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  id="social"
                  checked={socialized}
                  onCheckedChange={setSocialized}
                  data-testid="input-socialized"
                />
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
              <p className="text-sm text-destructive" data-testid="error-message">
                {error}
              </p>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full"
              data-testid="button-submit-checkin"
            >
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Save Check-in
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function SliderField({
  label,
  value,
  onChange,
  min,
  max,
  step,
  unit,
  hint,
  testId,
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
        <Label className="text-base font-medium">
          {label} ({display})
        </Label>
        {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
      </div>
      <Slider
        value={[value]}
        onValueChange={(v) => onChange(v[0])}
        min={min}
        max={max}
        step={step}
        data-testid={testId}
      />
    </div>
  );
}
