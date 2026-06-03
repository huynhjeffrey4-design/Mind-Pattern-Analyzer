import { Router, type IRouter } from "express";
import { eq, desc } from "drizzle-orm";
import { db, journalEntriesTable } from "@workspace/db";
import { anthropic } from "@workspace/integrations-anthropic-ai";
import {
  ListJournalEntriesQueryParams,
  ListJournalEntriesResponse,
  CreateJournalEntryBody,
  GetJournalEntryParams,
  GetJournalEntryResponse,
  UpdateJournalEntryParams,
  UpdateJournalEntryBody,
  UpdateJournalEntryResponse,
  DeleteJournalEntryParams,
  AnalyzeJournalEntryParams,
  AnalyzeJournalEntryResponse,
} from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/journal", async (req, res): Promise<void> => {
  const query = ListJournalEntriesQueryParams.safeParse(req.query);
  const limit = query.success ? (query.data.limit ?? 20) : 20;
  const offset = query.success ? (query.data.offset ?? 0) : 0;

  const rows = await db
    .select()
    .from(journalEntriesTable)
    .orderBy(desc(journalEntriesTable.createdAt))
    .limit(limit)
    .offset(offset);

  res.json(ListJournalEntriesResponse.parse(rows));
});

router.post("/journal", async (req, res): Promise<void> => {
  const parsed = CreateJournalEntryBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const [row] = await db.insert(journalEntriesTable).values(parsed.data).returning();
  res.status(201).json(GetJournalEntryResponse.parse(row));
});

router.get("/journal/:id", async (req, res): Promise<void> => {
  const params = GetJournalEntryParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [row] = await db
    .select()
    .from(journalEntriesTable)
    .where(eq(journalEntriesTable.id, params.data.id));

  if (!row) {
    res.status(404).json({ error: "Journal entry not found" });
    return;
  }

  res.json(GetJournalEntryResponse.parse(row));
});

router.patch("/journal/:id", async (req, res): Promise<void> => {
  const params = UpdateJournalEntryParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const parsed = UpdateJournalEntryBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const updates: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(parsed.data)) {
    if (v !== undefined) updates[k] = v;
  }

  const [row] = await db
    .update(journalEntriesTable)
    .set(updates)
    .where(eq(journalEntriesTable.id, params.data.id))
    .returning();

  if (!row) {
    res.status(404).json({ error: "Journal entry not found" });
    return;
  }

  res.json(UpdateJournalEntryResponse.parse(row));
});

router.delete("/journal/:id", async (req, res): Promise<void> => {
  const params = DeleteJournalEntryParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [row] = await db
    .delete(journalEntriesTable)
    .where(eq(journalEntriesTable.id, params.data.id))
    .returning();

  if (!row) {
    res.status(404).json({ error: "Journal entry not found" });
    return;
  }

  res.sendStatus(204);
});

const CRISIS_KEYWORDS = [
  "suicid", "kill myself", "end my life", "self-harm", "self harm",
  "hurt myself", "not worth living", "better off dead", "want to die",
];

router.post("/journal/:id/analyze", async (req, res): Promise<void> => {
  const params = AnalyzeJournalEntryParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [entry] = await db
    .select()
    .from(journalEntriesTable)
    .where(eq(journalEntriesTable.id, params.data.id));

  if (!entry) {
    res.status(404).json({ error: "Journal entry not found" });
    return;
  }

  const contentLower = entry.content.toLowerCase();
  const hasCrisisSignals = CRISIS_KEYWORDS.some((kw) => contentLower.includes(kw));

  const message = await anthropic.messages.create({
    model: "claude-haiku-4-5",
    max_tokens: 8192,
    messages: [
      {
        role: "user",
        content: `Analyze the following personal journal entry for emotional themes and provide a brief, compassionate summary. 
        
IMPORTANT RULES:
- Do NOT diagnose or label mental health conditions (no "you have depression", "anxiety disorder", etc.)
- Frame themes as observations, not diagnoses (e.g. "themes of feeling overwhelmed" not "anxiety")
- Keep the summary warm, non-judgmental, and focused on what the person expressed
- Return ONLY valid JSON, no markdown, no explanation outside the JSON

Return JSON in this exact format:
{
  "themes": ["theme1", "theme2", ...],
  "summary": "A 1-2 sentence compassionate summary of what the entry expresses"
}

Themes should be short (2-4 words each) and describe emotional content: e.g. "feeling overwhelmed", "low energy", "social connection", "work pressure", "sleep difficulties", "moments of joy", "sense of loneliness", "motivation", "gratitude", "worry about future".

Journal entry:
${entry.content}`,
      },
    ],
  });

  let themes: string[] = [];
  let summary = "";

  const block = message.content[0];
  if (block.type === "text") {
    try {
      const parsed = JSON.parse(block.text);
      themes = Array.isArray(parsed.themes) ? parsed.themes : [];
      summary = typeof parsed.summary === "string" ? parsed.summary : "";
    } catch {
      themes = [];
      summary = "We analyzed your entry and found it reflects a mix of personal experiences and emotions.";
    }
  }

  await db
    .update(journalEntriesTable)
    .set({
      themes: JSON.stringify(themes),
      aiSummary: summary,
    })
    .where(eq(journalEntriesTable.id, entry.id));

  const crisisMessage = hasCrisisSignals
    ? "If you're having thoughts of harming yourself, please reach out. Crisis Text Line: Text HOME to 741741. National Suicide Prevention Lifeline: 988. You are not alone."
    : null;

  const result = AnalyzeJournalEntryResponse.parse({
    themes,
    summary,
    hasCrisisSignals,
    crisisMessage,
  });

  res.json(result);
});

export default router;
