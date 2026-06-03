import { Router, type IRouter } from "express";
import { desc, gte, sql } from "drizzle-orm";
import { db, checkinsTable } from "@workspace/db";
import {
  GetDashboardSummaryResponse,
  GetMoodTrendQueryParams,
  GetMoodTrendResponse,
  GetPatternsResponse,
  GetWeeklySummaryResponse,
} from "@workspace/api-zod";
import { startOfWeek, endOfWeek, subDays, format, parseISO, getDay } from "date-fns";

const router: IRouter = Router();

router.get("/insights/dashboard", async (_req, res): Promise<void> => {
  const allCheckins = await db
    .select()
    .from(checkinsTable)
    .orderBy(desc(checkinsTable.date));

  const total = allCheckins.length;

  if (total === 0) {
    res.json(
      GetDashboardSummaryResponse.parse({
        totalCheckins: 0,
        avgMood: 0,
        avgSleep: 0,
        avgStress: 0,
        exerciseDaysThisWeek: 0,
        currentStreak: 0,
        bestDay: null,
        worstDay: null,
      })
    );
    return;
  }

  const avgMood = allCheckins.reduce((s, c) => s + c.moodRating, 0) / total;
  const avgSleep = allCheckins.reduce((s, c) => s + c.sleepHours, 0) / total;
  const avgStress = allCheckins.reduce((s, c) => s + c.stressLevel, 0) / total;

  const weekStart = startOfWeek(new Date(), { weekStartsOn: 1 });
  const exerciseDaysThisWeek = allCheckins.filter((c) => {
    const d = parseISO(c.date);
    return d >= weekStart && c.exercised;
  }).length;

  const sortedDates = [...allCheckins].sort((a, b) => b.date.localeCompare(a.date));
  let streak = 0;
  // Use midnight today so a check-in for today always counts as day 0 diff
  const todayMidnight = new Date();
  todayMidnight.setHours(0, 0, 0, 0);
  let current = todayMidnight;
  for (const c of sortedDates) {
    const rawDate = typeof c.date === "string" ? c.date.substring(0, 10) : format(c.date as unknown as Date, "yyyy-MM-dd");
    const d = parseISO(rawDate);
    d.setHours(0, 0, 0, 0);
    const diffDays = Math.round((current.getTime() - d.getTime()) / 86400000);
    if (diffDays <= 1) {
      streak++;
      current = d;
    } else {
      break;
    }
  }

  const best = allCheckins.reduce((a, b) => (a.moodRating > b.moodRating ? a : b));
  const worst = allCheckins.reduce((a, b) => (a.moodRating < b.moodRating ? a : b));

  res.json(
    GetDashboardSummaryResponse.parse({
      totalCheckins: total,
      avgMood: Math.round(avgMood * 10) / 10,
      avgSleep: Math.round(avgSleep * 10) / 10,
      avgStress: Math.round(avgStress * 10) / 10,
      exerciseDaysThisWeek,
      currentStreak: streak,
      bestDay: best.date,
      worstDay: worst.date,
    })
  );
});

router.get("/insights/mood-trend", async (req, res): Promise<void> => {
  const query = GetMoodTrendQueryParams.safeParse(req.query);
  const days = query.success ? (query.data.days ?? 30) : 30;

  const since = format(subDays(new Date(), days), "yyyy-MM-dd");

  const rows = await db
    .select()
    .from(checkinsTable)
    .where(gte(checkinsTable.date, since))
    .orderBy(checkinsTable.date);

  res.json(
    GetMoodTrendResponse.parse(
      rows.map((r) => ({
        date: r.date,
        moodRating: r.moodRating,
        stressLevel: r.stressLevel,
        sleepHours: r.sleepHours,
      }))
    )
  );
});

router.get("/insights/patterns", async (_req, res): Promise<void> => {
  const checkins = await db
    .select()
    .from(checkinsTable)
    .orderBy(desc(checkinsTable.date))
    .limit(60);

  const patterns: Array<{
    id: string;
    type: "sleep_mood" | "exercise_mood" | "stress_workload" | "social_mood" | "weekend_stress";
    description: string;
    confidence: number;
    suggestion: string | null;
  }> = [];

  if (checkins.length >= 5) {
    const lowSleep = checkins.filter((c) => c.sleepHours < 6);
    const goodSleep = checkins.filter((c) => c.sleepHours >= 7);
    if (lowSleep.length >= 3 && goodSleep.length >= 3) {
      const avgMoodLowSleep = lowSleep.reduce((s, c) => s + c.moodRating, 0) / lowSleep.length;
      const avgMoodGoodSleep = goodSleep.reduce((s, c) => s + c.moodRating, 0) / goodSleep.length;
      const diff = avgMoodGoodSleep - avgMoodLowSleep;
      if (diff >= 1.0) {
        const confidence = Math.min(0.95, 0.5 + diff * 0.12);
        patterns.push({
          id: "sleep_mood",
          type: "sleep_mood",
          description: `Your mood tends to be ${diff.toFixed(1)} points lower on days after less than 6 hours of sleep (avg mood: ${avgMoodLowSleep.toFixed(1)} vs ${avgMoodGoodSleep.toFixed(1)} on well-rested days).`,
          confidence: Math.round(confidence * 100) / 100,
          suggestion: "Try to prioritize 7–8 hours of sleep, especially before high-stress days.",
        });
      }
    }

    const exerciseDays = checkins.filter((c) => c.exercised);
    const noExerciseDays = checkins.filter((c) => !c.exercised);
    if (exerciseDays.length >= 3 && noExerciseDays.length >= 3) {
      const avgMoodExercise = exerciseDays.reduce((s, c) => s + c.moodRating, 0) / exerciseDays.length;
      const avgMoodNoExercise = noExerciseDays.reduce((s, c) => s + c.moodRating, 0) / noExerciseDays.length;
      const diff = avgMoodExercise - avgMoodNoExercise;
      if (diff >= 0.7) {
        const confidence = Math.min(0.93, 0.45 + diff * 0.15);
        patterns.push({
          id: "exercise_mood",
          type: "exercise_mood",
          description: `Exercise days are associated with a ${diff.toFixed(1)}-point mood boost (avg: ${avgMoodExercise.toFixed(1)} vs ${avgMoodNoExercise.toFixed(1)} on rest days).`,
          confidence: Math.round(confidence * 100) / 100,
          suggestion: "Your mood tends to improve after exercise. Consider short walks during stressful weeks.",
        });
      }
    }

    const socialDays = checkins.filter((c) => c.socialized);
    const soloDay = checkins.filter((c) => !c.socialized);
    if (socialDays.length >= 3 && soloDay.length >= 3) {
      const avgMoodSocial = socialDays.reduce((s, c) => s + c.moodRating, 0) / socialDays.length;
      const avgMoodSolo = soloDay.reduce((s, c) => s + c.moodRating, 0) / soloDay.length;
      const diff = avgMoodSocial - avgMoodSolo;
      if (diff >= 0.8) {
        const confidence = Math.min(0.90, 0.4 + diff * 0.13);
        patterns.push({
          id: "social_mood",
          type: "social_mood",
          description: `Days with social interaction are linked to a ${diff.toFixed(1)}-point higher mood on average.`,
          confidence: Math.round(confidence * 100) / 100,
          suggestion: "Social connection seems to lift your mood. Try to schedule regular time with people you enjoy.",
        });
      }
    }

    const withWorkload = checkins.filter((c) => c.workloadLevel != null);
    if (withWorkload.length >= 5) {
      const highWorkload = withWorkload.filter((c) => (c.workloadLevel ?? 0) >= 7);
      const lowWorkload = withWorkload.filter((c) => (c.workloadLevel ?? 0) <= 4);
      if (highWorkload.length >= 2 && lowWorkload.length >= 2) {
        const avgStressHigh = highWorkload.reduce((s, c) => s + c.stressLevel, 0) / highWorkload.length;
        const avgStressLow = lowWorkload.reduce((s, c) => s + c.stressLevel, 0) / lowWorkload.length;
        const diff = avgStressHigh - avgStressLow;
        if (diff >= 1.5) {
          const confidence = Math.min(0.88, 0.42 + diff * 0.10);
          patterns.push({
            id: "stress_workload",
            type: "stress_workload",
            description: `High workload days show ${diff.toFixed(1)}-point higher stress levels compared to lighter days.`,
            confidence: Math.round(confidence * 100) / 100,
            suggestion: "You may want to build recovery time into your schedule after high-workload periods.",
          });
        }
      }
    }

    const weekendCheckins = checkins.filter((c) => {
      const day = getDay(parseISO(c.date));
      return day === 0 || day === 6;
    });
    const weekdayCheckins = checkins.filter((c) => {
      const day = getDay(parseISO(c.date));
      return day >= 1 && day <= 5;
    });
    if (weekendCheckins.length >= 2 && weekdayCheckins.length >= 5) {
      const avgStressWeekend = weekendCheckins.reduce((s, c) => s + c.stressLevel, 0) / weekendCheckins.length;
      const avgStressWeekday = weekdayCheckins.reduce((s, c) => s + c.stressLevel, 0) / weekdayCheckins.length;
      const diff = avgStressWeekend - avgStressWeekday;
      if (diff >= 1.0) {
        const confidence = Math.min(0.82, 0.4 + diff * 0.08);
        patterns.push({
          id: "weekend_stress",
          type: "weekend_stress",
          description: `Your stress levels tend to be higher on weekends compared to weekdays — possibly Sunday anxiety.`,
          confidence: Math.round(confidence * 100) / 100,
          suggestion: "Try a relaxing Sunday routine to ease into the week ahead.",
        });
      }
    }
  }

  res.json(GetPatternsResponse.parse(patterns));
});

router.get("/insights/weekly-summary", async (_req, res): Promise<void> => {
  const weekStart = startOfWeek(new Date(), { weekStartsOn: 1 });
  const weekEnd = endOfWeek(new Date(), { weekStartsOn: 1 });

  const weekStartStr = format(weekStart, "yyyy-MM-dd");
  const weekEndStr = format(weekEnd, "yyyy-MM-dd");

  const checkins = await db
    .select()
    .from(checkinsTable)
    .where(gte(checkinsTable.date, weekStartStr))
    .orderBy(checkinsTable.date);

  const count = checkins.length;
  const highlights: string[] = [];

  if (count === 0) {
    res.json(
      GetWeeklySummaryResponse.parse({
        weekStart: weekStartStr,
        weekEnd: weekEndStr,
        avgMood: 0,
        avgSleep: 0,
        avgStress: 0,
        exerciseDays: 0,
        socialDays: 0,
        highlights: ["No check-ins this week yet — start today!"],
      })
    );
    return;
  }

  const avgMood = checkins.reduce((s, c) => s + c.moodRating, 0) / count;
  const avgSleep = checkins.reduce((s, c) => s + c.sleepHours, 0) / count;
  const avgStress = checkins.reduce((s, c) => s + c.stressLevel, 0) / count;
  const exerciseDays = checkins.filter((c) => c.exercised).length;
  const socialDays = checkins.filter((c) => c.socialized).length;

  if (avgMood >= 7) highlights.push("It's been a strong mood week overall.");
  else if (avgMood <= 4) highlights.push("This has been a tough week — be gentle with yourself.");

  if (avgSleep < 6) highlights.push("Sleep has been below 6 hours on average this week.");
  else if (avgSleep >= 7.5) highlights.push("Great sleep consistency this week.");

  if (exerciseDays >= 4) highlights.push(`You exercised ${exerciseDays} days this week — excellent.`);
  else if (exerciseDays === 0) highlights.push("No exercise logged this week — even a short walk counts.");

  if (socialDays >= 4) highlights.push("Strong social week — connection is good for wellbeing.");

  if (avgStress >= 7) highlights.push("High stress levels this week — consider a recovery activity.");

  if (highlights.length === 0) highlights.push("A balanced week. Keep tracking to see patterns emerge.");

  res.json(
    GetWeeklySummaryResponse.parse({
      weekStart: weekStartStr,
      weekEnd: weekEndStr,
      avgMood: Math.round(avgMood * 10) / 10,
      avgSleep: Math.round(avgSleep * 10) / 10,
      avgStress: Math.round(avgStress * 10) / 10,
      exerciseDays,
      socialDays,
      highlights,
    })
  );
});

export default router;
