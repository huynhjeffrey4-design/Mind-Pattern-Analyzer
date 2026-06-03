import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { journalService } from "@/services/journalService";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Loader2, BookOpen, Plus } from "lucide-react";
import { format } from "date-fns";
import RiskNotice from "@/components/RiskNotice";
import type { JournalResponse } from "@/types";

export default function Journal() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [formError, setFormError] = useState("");
  const [safetyFlagged, setSafetyFlagged] = useState(false);

  const { data: entries, isLoading, error } = useQuery({
    queryKey: ["journals"],
    queryFn: journalService.list,
  });

  const createMutation = useMutation({
    mutationFn: journalService.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["journals"] });
      if (data.safety_flagged) {
        setSafetyFlagged(true);
      }
      setTitle("");
      setContent("");
      setShowForm(false);
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(typeof detail === "string" ? detail : "Failed to save entry. Please try again.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    if (!content.trim()) {
      setFormError("Please write something before submitting.");
      return;
    }
    createMutation.mutate({ title: title.trim() || undefined, content: content.trim() });
  };

  return (
    <div className="p-8 max-w-4xl mx-auto w-full space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-serif text-foreground">Journal</h2>
          <p className="text-muted-foreground mt-2">A safe space for your thoughts.</p>
        </div>
        <Button
          onClick={() => { setShowForm(!showForm); setFormError(""); setSafetyFlagged(false); }}
          data-testid="button-new-journal"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Entry
        </Button>
      </div>

      {safetyFlagged && <RiskNotice />}

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Write a new entry</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">Title (optional)</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Give it a title…"
                  data-testid="input-journal-title"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="content">Entry</Label>
                <Textarea
                  id="content"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="What's on your mind today?"
                  className="min-h-[160px]"
                  data-testid="input-journal-content"
                />
              </div>
              {formError && (
                <p className="text-sm text-destructive" data-testid="journal-error">
                  {formError}
                </p>
              )}
              <div className="flex gap-3">
                <Button
                  type="submit"
                  disabled={createMutation.isPending}
                  data-testid="button-submit-journal"
                >
                  {createMutation.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : null}
                  Save entry
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setShowForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {error && (
        <p className="text-sm text-destructive">
          Failed to load journal entries. Please refresh.
        </p>
      )}

      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 rounded-xl border bg-card animate-pulse" />
          ))}
        </div>
      ) : !entries || entries.length === 0 ? (
        <Card className="bg-muted/50 border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <BookOpen className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-lg font-medium text-foreground">No entries yet</h3>
            <p className="text-muted-foreground mt-1 mb-6 max-w-sm">
              Write down your thoughts and feelings. Over time, patterns in your entries can surface
              useful insights.
            </p>
            <Button onClick={() => setShowForm(true)}>Start writing</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {entries.map((entry: JournalResponse) => (
            <JournalCard key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}

function JournalCard({ entry }: { entry: JournalResponse }) {
  const sentimentColor = (label: string | null) => {
    if (label === "positive") return "bg-green-100 text-green-800 border-green-200";
    if (label === "negative") return "bg-red-100 text-red-800 border-red-200";
    return "bg-secondary text-secondary-foreground";
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start gap-4">
          <CardTitle className="text-base font-medium">
            {entry.title || "Untitled Entry"}
          </CardTitle>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {format(new Date(entry.created_at), "MMM d, yyyy")}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground line-clamp-3">{entry.content}</p>
        <div className="flex flex-wrap gap-2 items-center">
          {entry.sentiment_label && (
            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${sentimentColor(entry.sentiment_label)}`}>
              {entry.sentiment_label}
            </span>
          )}
          {entry.keywords &&
            entry.keywords.map((kw, i) => (
              <Badge key={i} variant="secondary" className="font-normal text-xs">
                {kw}
              </Badge>
            ))}
        </div>
      </CardContent>
    </Card>
  );
}
