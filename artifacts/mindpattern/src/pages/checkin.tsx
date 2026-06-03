import { useState } from "react";
import { useLocation } from "wouter";
import { useCreateCheckin, getListCheckinsQueryKey } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Loader2 } from "lucide-react";

export default function CheckinNew() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const createCheckin = useCreateCheckin();
  
  const [mood, setMood] = useState(5);
  const [stress, setStress] = useState(5);
  const [sleep, setSleep] = useState(7);
  const [workload, setWorkload] = useState(5);
  const [exercised, setExercised] = useState(false);
  const [socialized, setSocialized] = useState(false);
  const [notes, setNotes] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createCheckin.mutate({
      data: {
        date: new Date().toISOString(),
        moodRating: mood,
        stressLevel: stress,
        sleepHours: sleep,
        workloadLevel: workload,
        exercised,
        socialized,
        notes: notes || null
      }
    }, {
      onSuccess: () => {
        toast({ title: "Check-in saved", description: "Your daily check-in has been recorded." });
        queryClient.invalidateQueries({ queryKey: getListCheckinsQueryKey() });
        setLocation("/history");
      },
      onError: () => {
        toast({ title: "Error", description: "Failed to save check-in", variant: "destructive" });
      }
    });
  };

  return (
    <div className="p-8 max-w-2xl mx-auto w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h2 className="text-3xl font-serif text-foreground">Daily Check-in</h2>
        <p className="text-muted-foreground mt-2">Take a moment to reflect on your day.</p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-8">
            <div className="space-y-4">
              <div className="flex justify-between">
                <Label className="text-base font-medium">Mood ({mood}/10)</Label>
                <span className="text-sm text-muted-foreground">1=Terrible, 10=Excellent</span>
              </div>
              <Slider value={[mood]} onValueChange={v => setMood(v[0])} min={1} max={10} step={1} data-testid="input-mood" />
            </div>

            <div className="space-y-4">
              <div className="flex justify-between">
                <Label className="text-base font-medium">Stress ({stress}/10)</Label>
                <span className="text-sm text-muted-foreground">1=Calm, 10=Overwhelmed</span>
              </div>
              <Slider value={[stress]} onValueChange={v => setStress(v[0])} min={1} max={10} step={1} data-testid="input-stress" />
            </div>

            <div className="space-y-4">
              <div className="flex justify-between">
                <Label className="text-base font-medium">Sleep ({sleep} hrs)</Label>
              </div>
              <Slider value={[sleep]} onValueChange={v => setSleep(v[0])} min={0} max={24} step={0.5} data-testid="input-sleep" />
            </div>
            
            <div className="space-y-4">
              <div className="flex justify-between">
                <Label className="text-base font-medium">Workload ({workload}/10)</Label>
              </div>
              <Slider value={[workload]} onValueChange={v => setWorkload(v[0])} min={1} max={10} step={1} data-testid="input-workload" />
            </div>

            <div className="flex items-center gap-6">
              <div className="flex items-center space-x-2">
                <Switch checked={exercised} onCheckedChange={setExercised} id="exercise" data-testid="input-exercised" />
                <Label htmlFor="exercise">Exercised</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Switch checked={socialized} onCheckedChange={setSocialized} id="social" data-testid="input-socialized" />
                <Label htmlFor="social">Socialized</Label>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-base font-medium">Notes (Optional)</Label>
              <Textarea 
                value={notes} 
                onChange={e => setNotes(e.target.value)} 
                placeholder="How did you feel today? Any specific events?"
                className="min-h-[100px]"
                data-testid="input-notes"
              />
            </div>

            <Button type="submit" disabled={createCheckin.isPending} className="w-full" data-testid="button-submit-checkin">
              {createCheckin.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Save Check-in
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
