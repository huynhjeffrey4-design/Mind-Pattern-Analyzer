import { apiClient } from "@/lib/api";
import type { CheckInCreate, CheckInUpdate, CheckInResponse } from "@/types";

export const checkInService = {
  create: async (data: CheckInCreate): Promise<CheckInResponse> => {
    const res = await apiClient.post<CheckInResponse>("/checkins", data);
    return res.data;
  },

  update: async (id: number, data: CheckInUpdate): Promise<CheckInResponse> => {
    const res = await apiClient.patch<CheckInResponse>(`/checkins/${id}`, data);
    return res.data;
  },

  getToday: async (): Promise<CheckInResponse | null> => {
    // Pass the browser's local date so the server lookup matches regardless of
    // timezone differences between the client and the UTC server.
    const today = new Date().toLocaleDateString("en-CA"); // yyyy-MM-dd in local TZ
    try {
      const res = await apiClient.get<CheckInResponse>(`/checkins/today?date=${today}`);
      return res.data;
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 404) return null;
      throw err;
    }
  },

  list: async (limit = 50): Promise<CheckInResponse[]> => {
    const res = await apiClient.get<CheckInResponse[]>(`/checkins?limit=${limit}`);
    return res.data;
  },

  get: async (id: number): Promise<CheckInResponse> => {
    const res = await apiClient.get<CheckInResponse>(`/checkins/${id}`);
    return res.data;
  },
};
