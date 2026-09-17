/** Client for GhostlyAI.in data, proxied through our own backend at /admin/ghostly/* (see
 * backend/app/api/admin/ghostly.py). The GhostlyAI API key never reaches the phone — every
 * call here goes through our own JWT-authed backend, same as the rest of this app.
 *
 * The exact shape of GhostlyAI's responses isn't confirmed yet (their auth header name is
 * still being tracked down), so every type below is intentionally loose (`AnyRecord`) and
 * every screen renders defensively via `lib/ghostlyFormat.ts` + `KeyValueList` rather than
 * assuming specific field names. */
import { apiClient } from "./api";
import type { AnyRecord } from "./ghostlyFormat";

export async function getGhostlyStats(): Promise<AnyRecord> {
  const { data } = await apiClient.get<AnyRecord>("/admin/ghostly/stats");
  return data;
}

export async function getGhostlyEmailStats(): Promise<AnyRecord> {
  const { data } = await apiClient.get<AnyRecord>("/admin/ghostly/email-stats");
  return data;
}

/** The upstream API's list endpoints don't have a confirmed envelope shape (could be a bare
 * array, or `{items: [...]}` / `{users: [...]}` / `{data: [...]}`), so this pulls out the
 * first array it finds anywhere in the response, at any depth up to 2 levels. */
export function extractList(payload: unknown): AnyRecord[] {
  if (Array.isArray(payload)) return payload.filter((x): x is AnyRecord => typeof x === "object" && x !== null);
  if (payload && typeof payload === "object") {
    for (const value of Object.values(payload as AnyRecord)) {
      if (Array.isArray(value)) {
        const arr = value.filter((x): x is AnyRecord => typeof x === "object" && x !== null);
        if (arr.length > 0 || value.length === 0) return arr;
      }
    }
    for (const value of Object.values(payload as AnyRecord)) {
      if (value && typeof value === "object" && !Array.isArray(value)) {
        const nested = extractList(value);
        if (nested.length > 0) return nested;
      }
    }
  }
  return [];
}

export async function listGhostlyUsers(params: { search?: string; filter?: string }): Promise<AnyRecord[]> {
  const { data } = await apiClient.get<AnyRecord>("/admin/ghostly/users", { params });
  return extractList(data);
}

export async function updateGhostlyUserPlan(
  userId: string,
  payload: { plan?: string; days?: number; blocked?: boolean; status?: string }
): Promise<AnyRecord> {
  const { data } = await apiClient.put<AnyRecord>(`/admin/ghostly/users/${encodeURIComponent(userId)}/plan`, payload);
  return data;
}

export async function listGhostlySupport(): Promise<AnyRecord[]> {
  const { data } = await apiClient.get<AnyRecord>("/admin/ghostly/support");
  return extractList(data);
}

export async function replyGhostlySupport(
  ticketId: string,
  text: string,
  resolve: boolean
): Promise<AnyRecord> {
  const { data } = await apiClient.post<AnyRecord>(`/admin/ghostly/support/${encodeURIComponent(ticketId)}/reply`, {
    text,
    resolve,
  });
  return data;
}

export async function updateGhostlySupportStatus(ticketId: string, status: string): Promise<AnyRecord> {
  const { data } = await apiClient.put<AnyRecord>(`/admin/ghostly/support/${encodeURIComponent(ticketId)}`, { status });
  return data;
}

export async function listGhostlyAnnouncements(): Promise<AnyRecord[]> {
  const { data } = await apiClient.get<AnyRecord>("/admin/ghostly/announcements");
  return extractList(data);
}

export async function createGhostlyAnnouncement(title: string, body: string): Promise<AnyRecord> {
  const { data } = await apiClient.post<AnyRecord>("/admin/ghostly/announcements", { title, body });
  return data;
}

export async function sendGhostlyAnnouncement(announcementId: string): Promise<AnyRecord> {
  const { data } = await apiClient.post<AnyRecord>(`/admin/ghostly/announcements/${encodeURIComponent(announcementId)}/send`);
  return data;
}

export async function sendGhostlyEmail(to: string, subject: string, body: string): Promise<AnyRecord> {
  const { data } = await apiClient.post<AnyRecord>("/admin/ghostly/send-email", { to, subject, body });
  return data;
}

export async function getGhostlyConfig(): Promise<AnyRecord> {
  const { data } = await apiClient.get<AnyRecord>("/admin/ghostly/config");
  return data;
}

export async function updateGhostlyConfig(patch: AnyRecord): Promise<AnyRecord> {
  const { data } = await apiClient.put<AnyRecord>("/admin/ghostly/config", patch);
  return data;
}
