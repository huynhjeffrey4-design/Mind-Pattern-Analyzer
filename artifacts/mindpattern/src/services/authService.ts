import { apiClient } from "@/lib/api";
import type { RegisterRequest, LoginRequest, TokenResponse, CurrentUser } from "@/types";

export const authService = {
  register: async (data: RegisterRequest): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>("/auth/register", data);
    return res.data;
  },

  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>("/auth/login", data);
    return res.data;
  },

  me: async (): Promise<CurrentUser> => {
    const res = await apiClient.get<CurrentUser>("/auth/me");
    return res.data;
  },
};
