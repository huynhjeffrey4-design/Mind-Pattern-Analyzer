import { Router, type IRouter } from "express";
import { eq, desc } from "drizzle-orm";
import { db, checkinsTable } from "@workspace/db";
import {
  ListCheckinsQueryParams,
  ListCheckinsResponse,
  CreateCheckinBody,
  GetCheckinParams,
  GetCheckinResponse,
  UpdateCheckinParams,
  UpdateCheckinBody,
  UpdateCheckinResponse,
  DeleteCheckinParams,
} from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/checkins", async (req, res): Promise<void> => {
  const query = ListCheckinsQueryParams.safeParse(req.query);
  const limit = query.success ? (query.data.limit ?? 30) : 30;
  const offset = query.success ? (query.data.offset ?? 0) : 0;

  const rows = await db
    .select()
    .from(checkinsTable)
    .orderBy(desc(checkinsTable.date))
    .limit(limit)
    .offset(offset);

  res.json(ListCheckinsResponse.parse(rows));
});

router.post("/checkins", async (req, res): Promise<void> => {
  const parsed = CreateCheckinBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const dateStr = parsed.data.date instanceof Date
    ? parsed.data.date.toISOString().split("T")[0]
    : String(parsed.data.date);

  const [row] = await db
    .insert(checkinsTable)
    .values({ ...parsed.data, date: dateStr })
    .returning();
  res.status(201).json(GetCheckinResponse.parse(row));
});

router.get("/checkins/:id", async (req, res): Promise<void> => {
  const params = GetCheckinParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [row] = await db
    .select()
    .from(checkinsTable)
    .where(eq(checkinsTable.id, params.data.id));

  if (!row) {
    res.status(404).json({ error: "Check-in not found" });
    return;
  }

  res.json(GetCheckinResponse.parse(row));
});

router.patch("/checkins/:id", async (req, res): Promise<void> => {
  const params = UpdateCheckinParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const parsed = UpdateCheckinBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const updates: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(parsed.data)) {
    if (v !== undefined) updates[k] = v;
  }

  const [row] = await db
    .update(checkinsTable)
    .set(updates)
    .where(eq(checkinsTable.id, params.data.id))
    .returning();

  if (!row) {
    res.status(404).json({ error: "Check-in not found" });
    return;
  }

  res.json(UpdateCheckinResponse.parse(row));
});

router.delete("/checkins/:id", async (req, res): Promise<void> => {
  const params = DeleteCheckinParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [row] = await db
    .delete(checkinsTable)
    .where(eq(checkinsTable.id, params.data.id))
    .returning();

  if (!row) {
    res.status(404).json({ error: "Check-in not found" });
    return;
  }

  res.sendStatus(204);
});

export default router;
