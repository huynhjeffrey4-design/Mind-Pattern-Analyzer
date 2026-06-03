import { apiClient } from "@/lib/api";
import type { JournalCreate, JournalResponse } from "@/types";

export const journalService = {
  create: async (data: JournalCreate): Promise<JournalResponse> => {
    const res = await apiClient.post<JournalResponse>("/journals", data);
    return res.data;
  },

  list: async (): Promise<JournalResponse[]> => {
    const res = await apiClient.get<JournalResponse[]>("/journals");
    return res.data;
  },

  get: async (id: number): Promise<JournalResponse> => {
    const res = await apiClient.get<JournalResponse>(`/journals/${id}`);
    return res.data;
  },
};
