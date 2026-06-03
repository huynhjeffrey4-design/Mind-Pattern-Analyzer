import { useListJournalEntries } from "@workspace/api-client-react";
import { Link } from "wouter";
import { format } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function Journal() {
  const { data: entries, isLoading } = useListJournalEntries();

  if (isLoading) {
    return <div className="flex h-full items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="p-8 max-w-4xl mx-auto w-full space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-serif text-foreground">Journal</h2>
          <p className="text-muted-foreground mt-2">A safe space for your thoughts.</p>
        </div>
        <Link href="/journal/new">
          <Button data-testid="button-new-journal">
            <Plus className="w-4 h-4 mr-2" />
            New Entry
          </Button>
        </Link>
      </div>

      {!entries || entries.length === 0 ? (
        <Card className="bg-muted/50 border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Book className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-lg font-medium text-foreground">No entries yet</h3>
            <p className="text-muted-foreground mt-1 mb-6 max-w-sm">Write down your thoughts and feelings. Over time, AI can help you find patterns in what you write.</p>
            <Link href="/journal/new">
              <Button>Start writing</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {entries.map((entry) => {
            const themes = entry.themes ? JSON.parse(entry.themes) : [];
            return (
              <Link key={entry.id} href={`/journal/${entry.id}`}>
                <Card className="hover:bg-accent/10 transition-colors cursor-pointer border hover:border-accent">
                  <CardHeader className="pb-2">
                    <div className="flex justify-between items-start">
                      <CardTitle className="text-lg font-medium">
                        {entry.title || "Untitled Entry"}
                      </CardTitle>
                      <span className="text-sm text-muted-foreground whitespace-nowrap ml-4">
                        {format(new Date(entry.createdAt), "MMM d, yyyy")}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
                      {entry.content}
                    </p>
                    {themes.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {themes.map((theme: string, i: number) => (
                          <Badge key={i} variant="secondary" className="font-normal text-xs">{theme}</Badge>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  );
}

import { Book } from "lucide-react";