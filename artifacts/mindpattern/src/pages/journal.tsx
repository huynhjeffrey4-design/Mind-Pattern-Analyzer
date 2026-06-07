import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { journalService } from "@/services/journalService";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Loader2, BookOpen, Plus, Trash2, X } from "lucide-react";
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

  const [viewEntry, setViewEntry] = useState<JournalResponse | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: entries, isLoading, error } = useQuery({
    queryKey: ["journals"],
    queryFn: journalService.list,
  });

  const createMutation = useMutation({
    mutationFn: journalService.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["journals"] });
      if (data.safety_flagged) setSafetyFlagged(true);
      setTitle("");
      setContent("");
      setShowForm(false);
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(typeof detail === "string" ? detail : "Failed to save entry. Please try again.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: journalService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journals"] });
      setViewEntry(null);
      setConfirmDelete(false);
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

  const openEntry = (entry: JournalResponse) => {
    setViewEntry(entry);
    setConfirmDelete(false);
  };

  const closeEntry = () => {
    setViewEntry(null);
    setConfirmDelete(false);
  };

  const handleDeleteClick = () => setConfirmDelete(true);

  const handleDeleteConfirm = () => {
    if (viewEntry) deleteMutation.mutate(viewEntry.id);
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
                  {createMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Save entry
                </Button>
                <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>
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
            <JournalCard key={entry.id} entry={entry} onClick={() => openEntry(entry)} />
          ))}
        </div>
      )}

      {/* Entry view modal */}
      <Dialog open={!!viewEntry} onOpenChange={(open) => { if (!open) closeEntry(); }}>
        <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col gap-0 p-0 overflow-hidden">
          {viewEntry && (
            <>
              <DialogHeader className="px-6 pt-6 pb-4 border-b shrink-0">
                <div className="flex items-start justify-between gap-4 pr-6">
                  <div className="min-w-0">
                    <DialogTitle className="text-xl font-serif leading-snug">
                      {viewEntry.title || "Untitled Entry"}
                    </DialogTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      {format(new Date(viewEntry.created_at), "EEEE, MMMM d, yyyy")}
                    </p>
                  </div>
                </div>
              </DialogHeader>

              <div className="flex-1 overflow-y-auto px-6 py-5">
                <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                  {viewEntry.content}
                </p>
              </div>

              {(viewEntry.sentiment_label || (viewEntry.keywords && viewEntry.keywords.length > 0)) && (
                <div className="px-6 py-3 border-t flex flex-wrap gap-2 items-center shrink-0">
                  {viewEntry.sentiment_label && (
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${sentimentColor(viewEntry.sentiment_label)}`}>
                      {viewEntry.sentiment_label}
                    </span>
                  )}
                  {viewEntry.keywords?.map((kw, i) => (
                    <Badge key={i} variant="secondary" className="font-normal text-xs">
                      {kw}
                    </Badge>
                  ))}
                </div>
              )}

              <div className="px-6 py-4 border-t shrink-0 flex items-center justify-between">
                {!confirmDelete ? (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={handleDeleteClick}
                      data-testid="button-delete-journal"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete entry
                    </Button>
                    <Button variant="outline" size="sm" onClick={closeEntry}>
                      Close
                    </Button>
                  </>
                ) : (
                  <>
                    <p className="text-sm text-muted-foreground">
                      Permanently delete this entry?
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setConfirmDelete(false)}
                        disabled={deleteMutation.isPending}
                      >
                        <X className="w-4 h-4 mr-1" />
                        Cancel
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={handleDeleteConfirm}
                        disabled={deleteMutation.isPending}
                        data-testid="button-confirm-delete-journal"
                      >
                        {deleteMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                        Yes, delete
                      </Button>
                    </div>
                  </>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function sentimentColor(label: string | null) {
  if (label === "positive") return "bg-green-100 text-green-800 border-green-200";
  if (label === "negative") return "bg-red-100 text-red-800 border-red-200";
  return "bg-secondary text-secondary-foreground";
}

function JournalCard({
  entry,
  onClick,
}: {
  entry: JournalResponse;
  onClick: () => void;
}) {
  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30 group"
      onClick={onClick}
      data-testid={`journal-card-${entry.id}`}
    >
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start gap-4">
          <CardTitle className="text-base font-medium group-hover:text-primary transition-colors">
            {entry.title || "Untitled Entry"}
          </CardTitle>
          <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0">
            {format(new Date(entry.created_at), "MMM d, yyyy")}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground line-clamp-3">{entry.content}</p>
        <div className="flex flex-wrap gap-2 items-center justify-between">
          <div className="flex flex-wrap gap-2 items-center">
            {entry.sentiment_label && (
              <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${sentimentColor(entry.sentiment_label)}`}>
                {entry.sentiment_label}
              </span>
            )}
            {entry.keywords?.slice(0, 4).map((kw, i) => (
              <Badge key={i} variant="secondary" className="font-normal text-xs">
                {kw}
              </Badge>
            ))}
            {(entry.keywords?.length ?? 0) > 4 && (
              <span className="text-xs text-muted-foreground">
                +{(entry.keywords?.length ?? 0) - 4} more
              </span>
            )}
          </div>
          <span className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
            Click to read →
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
