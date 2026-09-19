import axios, { AxiosError, type AxiosInstance } from "axios";
import Constants from "expo-constants";

const API_URL =
  process.env.EXPO_PUBLIC_API_URL ||
  (Constants.expoConfig?.extra as { apiUrl?: string } | undefined)?.apiUrl ||
  "http://localhost:8000";

let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

export function setOnUnauthorized(cb: () => void) {
  onUnauthorized = cb;
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 20000,
});

apiClient.interceptors.request.use((config) => {
  if (authToken) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      onUnauthorized?.();
    }
    return Promise.reject(error);
  }
);

type ValidationIssue = { loc?: (string | number)[]; msg?: string };

export function apiErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: string | ValidationIssue[] } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    // FastAPI 422s carry a list of {loc, msg}; show those instead of "status code 422"
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((issue) => {
          const field = (issue.loc ?? []).filter((part) => part !== "body").join(" > ");
          return field ? `${field}: ${issue.msg ?? "invalid"}` : issue.msg ?? "invalid";
        })
        .join("\n");
    }
    if (error.code === "ECONNABORTED") return `The server took too long to respond (${API_URL}). Please try again.`;
    if (error.request && !error.response) {
      return `Could not reach the server (${API_URL}). Check your internet connection.`;
    }
    if (error.message) return error.message;
  }
  return fallback;
}

/** Direct, no-auth connectivity probe used by the login screen's diagnostics panel. */
export async function checkBackendConnection(): Promise<{ ok: boolean; detail: string }> {
  try {
    const res = await axios.get(`${API_URL}/health`, { timeout: 8000 });
    return { ok: true, detail: `${res.status} ${JSON.stringify(res.data)}` };
  } catch (err) {
    return { ok: false, detail: apiErrorMessage(err) };
  }
}

export { API_URL };

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type AdminRole = "owner" | "uploader";

export interface AdminOut {
  id: number;
  name: string;
  email: string;
  role: AdminRole;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface DashboardData {
  users: { total: number; active_profiles: number; onboarding: number; new_today: number };
  subscriptions: { paid: number; trial: number; expiring_3_days: number };
  revenue_inr: { today: number; month: number };
  jobs: { today: number; active: number };
  deliveries: { sent_today: number; clicks_today: number; ctr_today: number };
  last_7_days: { date: string; revenue_inr: number; signups: number }[];
}

export interface JobOut {
  id: number;
  title: string;
  company: string;
  category_id: number;
  category_slug: string | null;
  qualification: string | null;
  district: string | null;
  location_text: string | null;
  job_type: "govt" | "private" | "internship" | "wfh";
  salary: string | null;
  apply_link: string;
  last_date: string | null;
  description: string | null;
  status: "active" | "expired" | "deleted";
  created_at: string;
  sent_count: number;
  click_count: number;
}

export interface JobIn {
  title: string;
  company: string;
  category_slug: string;
  qualification?: string | null;
  district?: string | null;
  location_text?: string | null;
  job_type: "govt" | "private" | "internship" | "wfh";
  salary?: string | null;
  apply_link: string;
  last_date?: string | null;
  description?: string | null;
}

export interface CategoryOut {
  id: number;
  slug: string;
  name: string;
  name_mr: string | null;
  name_hi: string | null;
  is_active: boolean;
  sort_order: number;
  users_count: number;
  jobs_count: number;
}

export interface UserRow {
  id: number;
  telegram_id: number | null; // null = signed up via the student app, never touched Telegram
  username: string | null;
  full_name: string | null;
  phone: string | null;
  district: string | null;
  language: string;
  status: string;
  access: "paid" | "trial" | "none";
  access_until: string | null;
  categories: string[];
  created_at: string;
}

export interface UserDetail {
  user: UserRow;
  profile: {
    education: string | null;
    course: string | null;
    skills: string[];
    experience_years: number;
    summary: string | null;
    has_resume: boolean;
  } | null;
  categories: string[];
  subscriptions: { start_at: string; end_at: string; source: string }[];
  payments: {
    id: number;
    amount_paise: number;
    status: string;
    paid_at: string | null;
    razorpay_payment_id: string | null;
  }[];
  recent_deliveries: { job_id: number; title: string | null; sent_at: string; clicked: boolean }[];
  stats: { sent: number; clicks: number };
}

export interface PaymentRow {
  id: number;
  user_id: number | null;
  user_name: string | null;
  user_phone: string | null;
  amount_inr: number;
  status: string;
  razorpay_payment_id: string | null;
  created_at: string;
  paid_at: string | null;
}

export interface SettingsData {
  price_inr: number;
  subscription_days: number;
  trial_days: number;
  digest_max_jobs: number;
  max_categories: number;
  teaser_every_hours: number;
  job_delay_minutes: number;
}

export interface StaffRow {
  id: number;
  name: string;
  email: string;
  role: AdminRole;
  is_active: boolean;
}

export interface JobDraft {
  title: string | null;
  company: string | null;
  category_slug: string;
  qualification: string | null;
  district: string | null;
  location_text: string | null;
  job_type: "govt" | "private" | "internship" | "wfh";
  salary: string | null;
  apply_link: string | null;
  last_date: string | null;
  description: string | null;
}

export interface BulkResult {
  created: number;
  duplicates: number;
  errors: { row?: number; index?: number; error: string }[];
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export async function login(email: string, password: string) {
  const { data } = await apiClient.post<{ access_token: string; admin: AdminOut }>(
    "/admin/auth/login",
    { email, password }
  );
  return data;
}

export async function fetchMe() {
  const { data } = await apiClient.get<AdminOut>("/admin/auth/me");
  return data;
}

export async function changePassword(oldPassword: string, newPassword: string) {
  await apiClient.post("/admin/auth/change-password", {
    old_password: oldPassword,
    new_password: newPassword,
  });
}

/** Registers (or clears, with null) this device's Expo push token against the logged-in admin. */
export async function setPushToken(token: string | null) {
  await apiClient.put("/admin/auth/push-token", { token });
}

// ---------------------------------------------------------------------------
// Dashboard / meta
// ---------------------------------------------------------------------------
export async function getDashboard() {
  const { data } = await apiClient.get<DashboardData>("/admin/dashboard");
  return data;
}

export async function getDistricts() {
  const { data } = await apiClient.get<string[]>("/admin/meta/districts");
  return data;
}

export async function getJobTypes() {
  const { data } = await apiClient.get<string[]>("/admin/meta/job-types");
  return data;
}

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------
export interface JobsQuery {
  q?: string;
  status?: string;
  category_id?: number;
  job_type?: string;
  date?: "today";
  page?: number;
  size?: number;
}

export async function listJobs(params: JobsQuery) {
  const { data } = await apiClient.get<Page<JobOut>>("/admin/jobs", { params });
  return data;
}

export async function getJob(id: number) {
  const { data } = await apiClient.get<JobOut>(`/admin/jobs/${id}`);
  return data;
}

export async function createJob(payload: JobIn) {
  const { data } = await apiClient.post<JobOut>("/admin/jobs", payload);
  return data;
}

export async function updateJob(id: number, payload: JobIn) {
  const { data } = await apiClient.put<JobOut>(`/admin/jobs/${id}`, payload);
  return data;
}

export async function deleteJob(id: number) {
  await apiClient.delete(`/admin/jobs/${id}`);
}

export async function batchCreateJobs(jobs: JobIn[]) {
  const { data } = await apiClient.post<BulkResult>("/admin/jobs/batch", { jobs });
  return data;
}

export async function bulkUploadJobs(file: { uri: string; name: string; mimeType?: string }) {
  const form = new FormData();
  form.append("file", { uri: file.uri, name: file.name, type: file.mimeType || "text/csv" } as any);
  const { data } = await apiClient.post<BulkResult>("/admin/jobs/bulk", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export function bulkTemplateUrl() {
  return `${API_URL}/admin/jobs/bulk/template`;
}

export async function aiParseJobs(text: string) {
  const { data } = await apiClient.post<{ drafts: JobDraft[] }>("/admin/jobs/ai-parse", { text });
  return data.drafts;
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------
export interface UsersQuery {
  q?: string;
  status?: string;
  access?: "paid" | "trial" | "none";
  expiring?: number;
  district?: string;
  page?: number;
  size?: number;
}

export async function listUsers(params: UsersQuery) {
  const { data } = await apiClient.get<Page<UserRow>>("/admin/users", { params });
  return data;
}

export async function getUser(id: number) {
  const { data } = await apiClient.get<UserDetail>(`/admin/users/${id}`);
  return data;
}

export async function extendUser(id: number, days: number, notify: boolean) {
  const { data } = await apiClient.post<{ access_until: string }>(`/admin/users/${id}/extend`, {
    days,
    notify,
  });
  return data;
}

export async function messageUser(id: number, text: string) {
  const { data } = await apiClient.post<{ result: string }>(`/admin/users/${id}/message`, { text });
  return data;
}

export async function blockUser(id: number) {
  await apiClient.post(`/admin/users/${id}/block`);
}

export async function unblockUser(id: number) {
  await apiClient.post(`/admin/users/${id}/unblock`);
}

export async function deleteUser(id: number) {
  await apiClient.delete(`/admin/users/${id}`);
}

export function resumeUrl(id: number) {
  return `${API_URL}/admin/users/${id}/resume`;
}

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------
export async function listCategories() {
  const { data } = await apiClient.get<CategoryOut[]>("/admin/categories");
  return data;
}

export async function createCategory(payload: {
  slug: string;
  name: string;
  name_mr?: string;
  name_hi?: string;
  sort_order?: number;
}) {
  const { data } = await apiClient.post("/admin/categories", payload);
  return data;
}

export async function updateCategory(
  id: number,
  payload: Partial<{ name: string; name_mr: string; name_hi: string; is_active: boolean; sort_order: number }>
) {
  const { data } = await apiClient.put(`/admin/categories/${id}`, payload);
  return data;
}

// ---------------------------------------------------------------------------
// Payments
// ---------------------------------------------------------------------------
export interface PaymentsQuery {
  status?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  size?: number;
}

export async function listPayments(params: PaymentsQuery) {
  const { data } = await apiClient.get<Page<PaymentRow>>("/admin/payments", { params });
  return data;
}

export async function syncPayment(id: number) {
  const { data } = await apiClient.post<PaymentRow>(`/admin/payments/${id}/sync`);
  return data;
}

export function paymentsExportUrl(params: PaymentsQuery) {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return `${API_URL}/admin/payments/export${qs ? `?${qs}` : ""}`;
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
export async function getSettings() {
  const { data } = await apiClient.get<SettingsData>("/admin/settings");
  return data;
}

export async function updateSettings(payload: Partial<SettingsData>) {
  const { data } = await apiClient.put<SettingsData>("/admin/settings", payload);
  return data;
}

// ---------------------------------------------------------------------------
// Broadcast
// ---------------------------------------------------------------------------
export type Audience = "all" | "paid" | "trial" | "expired";

export async function previewBroadcastCount(audience: Audience, categoryId?: number) {
  const { data } = await apiClient.post<{ count: number }>("/admin/broadcast/preview-count", {
    audience,
    category_id: categoryId,
  });
  return data.count;
}

export async function createBroadcast(text: string, audience: Audience, categoryId?: number) {
  const { data } = await apiClient.post<{ id: number; total: number }>("/admin/broadcast", {
    text,
    audience,
    category_id: categoryId,
  });
  return data;
}

export async function getBroadcast(id: number) {
  const { data } = await apiClient.get<{
    id: number;
    status: string;
    total: number;
    sent: number;
    failed: number;
  }>(`/admin/broadcast/${id}`);
  return data;
}

// ---------------------------------------------------------------------------
// Staff
// ---------------------------------------------------------------------------
export async function listStaff() {
  const { data } = await apiClient.get<StaffRow[]>("/admin/staff");
  return data;
}

export async function createStaff(payload: { name: string; email: string; password: string; role: AdminRole }) {
  const { data } = await apiClient.post("/admin/staff", payload);
  return data;
}

export async function updateStaff(id: number, payload: { is_active?: boolean; password?: string }) {
  const { data } = await apiClient.put(`/admin/staff/${id}`, payload);
  return data;
}

// ---------------------------------------------------------------------------
// Support inbox
// ---------------------------------------------------------------------------
export interface SupportThread {
  user_id: number;
  full_name: string | null;
  username: string | null;
  phone: string | null;
  status: string;
  last_message: string | null;
  last_direction: "in" | "out" | null;
  last_at: string | null;
  awaiting_reply: boolean;
}

export interface SupportMessageOut {
  id: number;
  direction: "in" | "out";
  text: string;
  created_at: string;
}

export interface SupportThreadDetail {
  user: { id: number; full_name: string | null; username: string | null; phone: string | null; status: string; language: string };
  messages: SupportMessageOut[];
}

export async function listSupportThreads(params: { status?: "open" | "all"; q?: string; page?: number; size?: number }) {
  const { data } = await apiClient.get<Page<SupportThread>>("/admin/support", { params });
  return data;
}

export async function getSupportThread(userId: number) {
  const { data } = await apiClient.get<SupportThreadDetail>(`/admin/support/${userId}`);
  return data;
}

export async function replySupport(userId: number, text: string) {
  const { data } = await apiClient.post<{ result: "ok" | "blocked" | "error" }>(`/admin/support/${userId}/reply`, { text });
  return data;
}

// ---------------------------------------------------------------------------
// Category delivery report
// ---------------------------------------------------------------------------
export interface CategoryDeliveryRow {
  category_id: number;
  slug: string;
  name: string;
  is_active: boolean;
  jobs: number;
  jobs_waiting_to_send: number;
  subscribers: number;
  sent: number;
  clicked: number;
  students_waiting: number;
}

export async function getDeliveryStats(days: number) {
  const { data } = await apiClient.get<{ days: number; job_delay_minutes: number; items: CategoryDeliveryRow[] }>(
    "/admin/categories/delivery-stats",
    { params: { days } }
  );
  return data;
}
