import { pgTable, text, serial, timestamp, integer, real, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const checkinsTable = pgTable("checkins", {
  id: serial("id").primaryKey(),
  date: text("date").notNull(),
  moodRating: integer("mood_rating").notNull(),
  stressLevel: integer("stress_level").notNull(),
  sleepHours: real("sleep_hours").notNull(),
  exercised: boolean("exercised").notNull().default(false),
  socialized: boolean("socialized").notNull().default(false),
  workloadLevel: integer("workload_level"),
  notes: text("notes"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const insertCheckinSchema = createInsertSchema(checkinsTable).omit({
  id: true,
  createdAt: true,
});
export type InsertCheckin = z.infer<typeof insertCheckinSchema>;
export type Checkin = typeof checkinsTable.$inferSelect;
