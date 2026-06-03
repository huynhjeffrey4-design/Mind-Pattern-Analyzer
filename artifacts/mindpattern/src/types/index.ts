export interface RegisterRequest {
  email: string;
  password: string;
  display_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: number;
  email: string;
  display_name: string | null;
  ai_analysis_enabled: boolean;
  weekly_summary_enabled: boolean;
}

export interface CheckInCreate {
  date: string;
  mood_rating: number;
  stress_level: number;
  sleep_hours: number;
  energy_level?: number;
  exercised: boolean;
  socialized: boolean;
  workload_level?: number;
  notes?: string;
}

export interface CheckInResponse {
  id: number;
  user_id: number;
  date: string;
  mood_rating: number;
  stress_level: number;
  sleep_hours: number;
  energy_level: number | null;
  exercised: boolean;
  socialized: boolean;
  workload_level: number | null;
  notes: string | null;
  created_at: string;
}

export interface JournalCreate {
  title?: string;
  content: string;
}

export interface JournalResponse {
  id: number;
  user_id: number;
  title: string | null;
  content: string;
  keywords: string[] | null;
  sentiment_score: number | null;
  sentiment_label: string | null;
  safety_flagged: boolean;
  created_at: string;
  updated_at: string;
}

export interface DashboardSummary {
  total_checkins: number;
  avg_mood: number | null;
  avg_stress: number | null;
  avg_sleep: number | null;
  current_streak: number;
}

export interface TrendPoint {
  date: string;
  value: number;
}

export interface MoodTrendResponse {
  trends: TrendPoint[];
}

export interface StressTrendResponse {
  trends: TrendPoint[];
}

export interface SleepMoodPoint {
  sleep_hours: number;
  mood_rating: number;
  date: string;
}

export interface SleepMoodResponse {
  data: SleepMoodPoint[];
}

export interface InsightResponse {
  id: number;
  user_id: number;
  insight_type: string;
  title: string;
  description: string;
  confidence: number | null;
  suggestion: string | null;
  created_at: string;
}

export interface InsightGenerateResponse {
  insights: InsightResponse[];
  generated_count: number;
}

export interface UserSettingsUpdate {
  ai_analysis_enabled?: boolean;
  weekly_summary_enabled?: boolean;
}

export interface UserSettingsResponse {
  id: number;
  email: string;
  display_name: string | null;
  ai_analysis_enabled: boolean;
  weekly_summary_enabled: boolean;
}
