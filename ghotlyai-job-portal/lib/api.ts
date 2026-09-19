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
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((issue) => {
          const field = (issue.loc ?? []).filter((part) => part !== "body").join(" > ");
          return field ? `${field}: ${issue.msg ?? "invalid"}` : issue.msg ?? "invalid";
        })
        .join("\n");
    }
    if (error.code === "ECONNABORTED") return `The server took too long to respond. Please try again.`;
    if (error.request && !error.response) {
      return "Could not reach the server. Check your internet connection.";
    }
    if (error.message) return error.message;
  }
  return fallback;
}

export { API_URL };

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface StudentOut {
  id: number;
  full_name: string | null;
  phone: string | null;
  district: string | null;
  language: string;
  job_types: string[];
  status: "onboarding" | "active" | "blocked" | "bot_blocked";
  category_ids: number[];
  has_access: boolean;
  in_trial: boolean;
  access_until: string | null;
}

export type NextStep = "name" | "district" | "profile" | "done";

export interface MeOut {
  user: StudentOut;
  next_step: NextStep;
}

export interface AuthOut extends MeOut {
  access_token: string;
  token_type: string;
  is_new_user: boolean;
}

export interface CategoryOut {
  id: number;
  slug: string;
  name: string;
}

export interface PublicSettings {
  price_inr: number;
  subscription_days: number;
  trial_days: number;
  max_categories: number;
}

export interface ResumeSummary {
  education: string | null;
  course: string | null;
  skills: string[];
  experience_years: number;
  summary: string | null;
  suggested_category_slugs: string[];
}

export type JobType = "govt" | "private" | "internship" | "wfh";

export interface JobOut {
  id: number;
  title: string;
  company: string;
  category_id: number;
  qualification: string | null;
  district: string | null;
  location_text: string | null;
  job_type: JobType;
  salary: string | null;
  description: string | null;
  last_date: string | null;
  created_at: string;
  apply_url: string;
  clicked: boolean;
}

export interface JobListOut {
  items: JobOut[];
  next_cursor: string | null;
}

export interface JobFilters {
  category_id?: number;
  job_type?: JobType;
  district?: string;
  q?: string;
}

export interface SupportMessageOut {
  id: number;
  direction: "in" | "out";
  text: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export async function loginWithPhone(idToken: string) {
  const { data } = await apiClient.post<AuthOut>("/student/auth/phone", { id_token: idToken });
  return data;
}

export async function fetchMe() {
  const { data } = await apiClient.get<MeOut>("/student/auth/me");
  return data;
}

export async function setPushToken(token: string | null) {
  await apiClient.put("/student/me/push-token", { token });
}

// ---------------------------------------------------------------------------
// Onboarding
// ---------------------------------------------------------------------------
export async function setName(fullName: string) {
  const { data } = await apiClient.put<MeOut>("/student/me/name", { full_name: fullName });
  return data;
}

export async function setDistrict(district: string) {
  const { data } = await apiClient.put<MeOut>("/student/me/district", { district });
  return data;
}

export async function uploadResume(file: { uri: string; name: string; mimeType?: string }) {
  const form = new FormData();
  form.append("file", { uri: file.uri, name: file.name, type: file.mimeType || "application/pdf" } as any);
  const { data } = await apiClient.post<ResumeSummary>("/student/me/resume", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function completeOnboarding(categoryIds: number[], jobTypes: JobType[]) {
  const { data } = await apiClient.post<MeOut>("/student/me/complete", {
    category_ids: categoryIds,
    job_types: jobTypes,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Meta (public, no auth needed)
// ---------------------------------------------------------------------------
export async function getCategories(lang: string = "mr") {
  const { data } = await apiClient.get<CategoryOut[]>("/student/categories", { params: { lang } });
  return data;
}

export async function getDistricts() {
  const { data } = await apiClient.get<{ districts: string[]; top: string[] }>("/student/districts");
  return data;
}

export async function getPublicSettings() {
  const { data } = await apiClient.get<PublicSettings>("/student/settings");
  return data;
}

// ---------------------------------------------------------------------------
// Jobs (browsable feed)
// ---------------------------------------------------------------------------
export async function browseJobs(filters: JobFilters, cursor?: string, limit = 20) {
  const { data } = await apiClient.get<JobListOut>("/student/jobs", {
    params: { ...filters, cursor, limit },
  });
  return data;
}

export async function getJob(id: number) {
  const { data } = await apiClient.get<JobOut>(`/student/jobs/${id}`);
  return data;
}

// ---------------------------------------------------------------------------
// Payments (native Razorpay Checkout SDK)
// ---------------------------------------------------------------------------
export interface CreateOrderOut {
  order_id: string;
  amount: number;
  currency: string;
  key_id: string;
}

export async function createPaymentOrder() {
  const { data } = await apiClient.post<CreateOrderOut>("/student/payments/order");
  return data;
}

export async function verifyPayment(payload: {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}) {
  const { data } = await apiClient.post<{ access_until: string | null }>("/student/payments/verify", payload);
  return data;
}

// ---------------------------------------------------------------------------
// Support
// ---------------------------------------------------------------------------
export async function getSupportThread() {
  const { data } = await apiClient.get<{ messages: SupportMessageOut[] }>("/student/support");
  return data.messages;
}

export async function sendSupportMessage(text: string) {
  const { data } = await apiClient.post<SupportMessageOut>("/student/support", { text });
  return data;
}
