import { create } from "zustand";

interface CurrentUser {
  id: number;
  email: string;
  display_name: string | null;
  ai_analysis_enabled: boolean;
  weekly_summary_enabled: boolean;
}

interface AuthState {
  accessToken: string | null;
  currentUser: CurrentUser | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: CurrentUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem("access_token"),
  currentUser: null,
  isAuthenticated: !!localStorage.getItem("access_token"),
  setAuth: (token, user) => {
    localStorage.setItem("access_token", token);
    set({ accessToken: token, currentUser: user, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem("access_token");
    set({ accessToken: null, currentUser: null, isAuthenticated: false });
  },
}));

export type { CurrentUser };
