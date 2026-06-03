import { apiClient } from "@/lib/api";
import type { CheckInCreate, CheckInResponse } from "@/types";

export const checkInService = {
  create: async (data: CheckInCreate): Promise<CheckInResponse> => {
    const res = await apiClient.post<CheckInResponse>("/checkins", data);
    return res.data;
  },

  list: async (): Promise<CheckInResponse[]> => {
    const res = await apiClient.get<CheckInResponse[]>("/checkins");
    return res.data;
  },

  get: async (id: number): Promise<CheckInResponse> => {
    const res = await apiClient.get<CheckInResponse>(`/checkins/${id}`);
    return res.data;
  },
};
