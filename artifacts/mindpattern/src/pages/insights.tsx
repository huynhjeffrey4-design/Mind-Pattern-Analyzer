import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { insightService } from "@/services/insightService";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, Sparkles, Info, TrendingUp, AlertCircle } from "lucide-react";
import { format } from "date-fns";
import type { InsightResponse } from "@/types";

const confidenceLabel = (c: number | null) => {
  if (c == null) return null;
  if (c >= 0.8) return "High confidence";
  if (c >= 0.5) return "Moderate confidence";
  return "Low confidence";
};

const typeIcon = (type: string) => {
  if (type === "not_enough_data") return <Info className="w-5 h-5 text-muted-foreground" />;
  if (type.includes("positive") || type.includes("improvement"))
    return <TrendingUp className="w-5 h-5 text-green-600" />;
  return <Sparkles className="w-5 h-5 text-primary" />;
};

function InsightCard({ insight }: { insight: InsightResponse }) {
  const isNeutral = insight.insight_type === "not_enough_data";

  return (
    <Card className={isNeutral ? "bg-muted/40 border-muted" : ""}>
      <CardHeader className="pb-2 flex flex-row items-start gap-3">
        <div className="mt-0.5">{typeIcon(insight.insight_type)}</div>
        <div className="flex-1 min-w-0">
          <CardTitle className="text-base font-medium">{insight.title}</CardTitle>
          {insight.confidence != null && !isNeutral && (
            <p className="text-xs text-muted-foreground mt-0.5">
              {confidenceLabel(insight.confidence)}
            </p>
          )}
        </div>
        <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0">
          {format(new Date(insight.created_at), "MMM d")}
        </span>
      </CardHeader>
      <CardContent className="space-y-2 pl-12">
        <p className="text-sm text-muted-foreground">{insight.description}</p>
        {insight.suggestion && !isNeutral && (
          <p className="text-sm text-foreground font-medium border-l-2 border-primary pl-3">
            {insight.suggestion}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function Insights() {
  const queryClient = useQueryClient();

  const { data: insights, isLoading, error } = useQuery({
    queryKey: ["insights"],
    queryFn: insightService.list,
  });

  const generateMutation = useMutation({
    mutationFn: insightService.generate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insights"] });
    },
  });

  return (
    <div className="p-8 max-w-4xl mx-auto w-full space-y-8 animate-in fade-in duration-500">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-3xl font-serif text-foreground">Insights</h2>
          <p className="text-muted-foreground mt-2">
            Patterns detected from your check-ins and journal entries.
          </p>
        </div>
        <Button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          data-testid="button-generate-insights"
        >
          {generateMutation.isPending ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4 mr-2" />
          )}
          Generate Insights
        </Button>
      </div>

      {generateMutation.isError && (
        <div className="flex gap-2 items-center text-sm text-destructive">
          <AlertCircle className="w-4 h-4 shrink-0" />
          Failed to generate insights. Please try again.
        </div>
      )}

      {generateMutation.isSuccess && (
        <div className="text-sm text-primary font-medium">
          ✓ Insights refreshed successfully.
        </div>
      )}

      {error && (
        <p className="text-sm text-destructive">Failed to load insights. Please refresh.</p>
      )}

      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-28 rounded-xl border bg-card animate-pulse" />
          ))}
        </div>
      ) : !insights || insights.length === 0 ? (
        <Card className="bg-muted/50 border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Sparkles className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-lg font-medium text-foreground">No insights yet</h3>
            <p className="text-muted-foreground mt-1 mb-6 max-w-sm">
              Log at least a few check-ins, then click "Generate Insights" to see patterns in your
              data.
            </p>
            <Button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : null}
              Generate Insights
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {insights.map((insight: InsightResponse) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}
    </div>
  );
}
