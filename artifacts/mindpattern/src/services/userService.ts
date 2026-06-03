import { apiClient } from "@/lib/api";
import type { UserSettingsUpdate, UserSettingsResponse } from "@/types";

export const userService = {
  getSettings: async (): Promise<UserSettingsResponse> => {
    const res = await apiClient.get<UserSettingsResponse>("/users/me/settings");
    return res.data;
  },

  updateSettings: async (data: UserSettingsUpdate): Promise<UserSettingsResponse> => {
    const res = await apiClient.put<UserSettingsResponse>("/users/me/settings", data);
    return res.data;
  },
};
