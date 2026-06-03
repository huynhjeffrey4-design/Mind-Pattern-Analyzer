import { apiClient } from "@/lib/api";
import type { DashboardSummary, MoodTrendResponse, StressTrendResponse, SleepMoodResponse } from "@/types";

export const dashboardService = {
  getSummary: async (): Promise<DashboardSummary> => {
    const res = await apiClient.get<DashboardSummary>("/dashboard/summary");
    return res.data;
  },

  getMoodTrends: async (): Promise<MoodTrendResponse> => {
    const res = await apiClient.get<MoodTrendResponse>("/dashboard/mood-trends");
    return res.data;
  },

  getStressTrends: async (): Promise<StressTrendResponse> => {
    const res = await apiClient.get<StressTrendResponse>("/dashboard/stress-trends");
    return res.data;
  },

  getSleepMood: async (): Promise<SleepMoodResponse> => {
    const res = await apiClient.get<SleepMoodResponse>("/dashboard/sleep-mood");
    return res.data;
  },
};
