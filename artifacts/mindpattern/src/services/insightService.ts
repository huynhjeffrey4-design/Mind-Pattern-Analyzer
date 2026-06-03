import { apiClient } from "@/lib/api";
import type { InsightResponse, InsightGenerateResponse } from "@/types";

export const insightService = {
  list: async (): Promise<InsightResponse[]> => {
    const res = await apiClient.get<InsightResponse[]>("/insights");
    return res.data;
  },

  generate: async (): Promise<InsightGenerateResponse> => {
    const res = await apiClient.post<InsightGenerateResponse>("/insights/generate");
    return res.data;
  },
};
