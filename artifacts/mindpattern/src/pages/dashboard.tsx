import { useQuery } from "@tanstack/react-query";
import { dashboardService } from "@/services/dashboardService";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { format } from "date-fns";
import { Loader2, Activity, Moon, Zap, Flame } from "lucide-react";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";

function StatCard({
  label,
  value,
  icon: Icon,
  sub,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  sub?: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <Icon className="w-4 h-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </CardContent>
    </Card>
  );
}

function LoadingCard({ className = "" }: { className?: string }) {
  return (
    <div className={`rounded-xl border bg-card animate-pulse h-40 ${className}`} />
  );
}

export default function Dashboard() {
  const { data: summary, isLoading: loadingSummary, error: summaryErr } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: dashboardService.getSummary,
  });

  const { data: moodData, isLoading: loadingMood } = useQuery({
    queryKey: ["mood-trends"],
    queryFn: dashboardService.getMoodTrends,
  });

  const { data: stressData, isLoading: loadingStress } = useQuery({
    queryKey: ["stress-trends"],
    queryFn: dashboardService.getStressTrends,
  });

  const { data: sleepMoodData, isLoading: loadingSleep } = useQuery({
    queryKey: ["sleep-mood"],
    queryFn: dashboardService.getSleepMood,
  });

  if (summaryErr) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Failed to load dashboard data. Please try refreshing.
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-3xl font-serif text-foreground">Welcome back</h2>
          <p className="text-muted-foreground mt-2">
            Here is a gentle overview of how you've been feeling recently.
          </p>
        </div>
        <Link href="/check-in">
          <Button data-testid="button-new-checkin">Log today</Button>
        </Link>
      </div>

      {loadingSummary ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <LoadingCard key={i} className="h-28" />
          ))}
        </div>
      ) : summary ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard
            label="Total Check-ins"
            value={String(summary.total_checkins)}
            icon={Activity}
            sub="all time"
          />
          <StatCard
            label="Avg Mood"
            value={summary.avg_mood != null ? `${summary.avg_mood.toFixed(1)}/5` : "—"}
            icon={Flame}
            sub="1–5 scale"
          />
          <StatCard
            label="Avg Stress"
            value={summary.avg_stress != null ? `${summary.avg_stress.toFixed(1)}/5` : "—"}
            icon={Zap}
            sub="1–5 scale"
          />
          <StatCard
            label="Avg Sleep"
            value={summary.avg_sleep != null ? `${summary.avg_sleep.toFixed(1)}h` : "—"}
            icon={Moon}
            sub="per night"
          />
        </div>
      ) : null}

      {summary && summary.current_streak > 0 && (
        <div className="rounded-lg bg-primary/10 border border-primary/20 px-5 py-3 text-sm text-primary font-medium">
          🔥 {summary.current_streak}-day streak — keep it going!
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Mood Over Time</CardTitle>
          </CardHeader>
          <CardContent className="h-56">
            {loadingMood ? (
              <div className="h-full flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : moodData && moodData.trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={moodData.trends}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(v) => format(new Date(v), "MMM d")}
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis hide domain={[0, 5]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    labelFormatter={(v) => format(new Date(v), "MMM d, yyyy")}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name="Mood"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2.5}
                    dot={{ r: 3, fill: "hsl(var(--primary))" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No mood data yet. Start logging check-ins!
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Stress Over Time</CardTitle>
          </CardHeader>
          <CardContent className="h-56">
            {loadingStress ? (
              <div className="h-full flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : stressData && stressData.trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stressData.trends}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(v) => format(new Date(v), "MMM d")}
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis hide domain={[0, 5]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    labelFormatter={(v) => format(new Date(v), "MMM d, yyyy")}
                  />
                  <Bar dataKey="value" name="Stress" fill="hsl(var(--destructive))" radius={[4, 4, 0, 0]} opacity={0.8} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No stress data yet. Start logging check-ins!
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sleep vs. Mood</CardTitle>
        </CardHeader>
        <CardContent className="h-56">
          {loadingSleep ? (
            <div className="h-full flex items-center justify-center">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : sleepMoodData && sleepMoodData.data.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="sleep_hours"
                  name="Sleep (hrs)"
                  type="number"
                  domain={[0, 12]}
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  label={{ value: "Sleep hours", position: "insideBottom", offset: -5, fontSize: 11 }}
                />
                <YAxis
                  dataKey="mood_rating"
                  name="Mood"
                  type="number"
                  domain={[0, 5]}
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  label={{ value: "Mood", angle: -90, position: "insideLeft", fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  cursor={{ strokeDasharray: "3 3" }}
                />
                <Scatter
                  data={sleepMoodData.data}
                  fill="hsl(var(--primary))"
                  opacity={0.7}
                />
              </ScatterChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
              Need more check-ins to show sleep vs. mood patterns.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
