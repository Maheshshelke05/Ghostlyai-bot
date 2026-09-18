/** Helpers for rendering GhostlyAI.in data whose exact field names aren't confirmed yet
 * (their auth header is still unknown, so the real response shape hasn't been seen). Every
 * screen renders a best-guess "nice" layout using common field-name candidates, PLUS a
 * generic key/value dump of every field the object actually has — so nothing is ever hidden
 * because a guessed name didn't match, and nothing crashes on an unexpected shape. */

export type AnyRecord = Record<string, unknown>;

/** Returns the first defined, non-null, non-empty-string value among candidate keys,
 * matching case-insensitively against the object's actual keys. */
export function firstOf(obj: AnyRecord | null | undefined, candidates: string[]): unknown {
  if (!obj) return undefined;
  const lowerMap = new Map(Object.keys(obj).map((k) => [k.toLowerCase(), k]));
  for (const candidate of candidates) {
    const realKey = lowerMap.get(candidate.toLowerCase());
    if (realKey === undefined) continue;
    const value = obj[realKey];
    if (value === null || value === undefined) continue;
    if (typeof value === "string" && value.trim() === "") continue;
    return value;
  }
  return undefined;
}

export function firstOfString(obj: AnyRecord | null | undefined, candidates: string[], fallback = ""): string {
  const value = firstOf(obj, candidates);
  return value === undefined ? fallback : String(value);
}

export function firstOfNumber(obj: AnyRecord | null | undefined, candidates: string[], fallback = 0): number {
  const value = firstOf(obj, candidates);
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : fallback;
}

/** Like `firstOf` but returns the actual matching key (original casing) instead of the value,
 * so a write-back can target the same field the API actually used rather than guessing a
 * fresh name and creating a duplicate. Falls back to the first candidate if nothing matched. */
export function firstOfKey(obj: AnyRecord | null | undefined, candidates: string[]): string {
  if (obj) {
    const lowerMap = new Map(Object.keys(obj).map((k) => [k.toLowerCase(), k]));
    for (const candidate of candidates) {
      const realKey = lowerMap.get(candidate.toLowerCase());
      if (realKey !== undefined) return realKey;
    }
  }
  return candidates[0];
}

export function firstOfBool(obj: AnyRecord | null | undefined, candidates: string[]): boolean | undefined {
  const value = firstOf(obj, candidates);
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    if (["true", "yes", "1"].includes(value.toLowerCase())) return true;
    if (["false", "no", "0"].includes(value.toLowerCase())) return false;
  }
  if (typeof value === "number") return value !== 0;
  return undefined;
}

/** "new_signups_today" -> "New signups today" */
export function humanizeKey(key: string): string {
  const spaced = key.replace(/[_-]+/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1).toLowerCase();
}

function looksLikeDate(key: string, value: string): boolean {
  if (!/date|_at$|time/i.test(key)) return false;
  const t = Date.parse(value);
  return !Number.isNaN(t);
}

export function formatDisplayDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) +
    (iso.includes("T") ? ` · ${d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}` : "");
}

/** Renders any scalar/array value as a short display string. Objects are summarized rather
 * than dumped inline (the caller should recurse into them as their own section instead). */
export function formatValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return value.toLocaleString("en-IN");
  if (typeof value === "string") {
    if (value.trim() === "") return "—";
    if (looksLikeDate(key, value)) return formatDisplayDate(value);
    return value;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return "None";
    if (value.every((v) => typeof v !== "object" || v === null)) return value.join(", ");
    return `${value.length} item${value.length === 1 ? "" : "s"}`;
  }
  if (typeof value === "object") return "See below";
  return String(value);
}

export const isPlainObject = (value: unknown): value is AnyRecord =>
  typeof value === "object" && value !== null && !Array.isArray(value);

/** Keys we never want in a generic "everything else" dump because they're already shown
 * front-and-centre by the screen, or are internal/noisy. */
export const COMMON_HIDDEN_KEYS = ["id", "_id", "uid", "user_id", "ticket_id"];

/** "Alice" / "Alice, Bob" / "Alice, Bob, Carol and 2 more users" - mirrors the backend's
 * _names_summary() (app/workers/ghostly_alerts.py) so the in-app toast and the OS push read
 * the same way for the same event. */
export function namesSummary(names: string[], noun: string): string {
  if (names.length === 1) return names[0];
  if (names.length <= 3) return names.join(", ");
  return `${names.slice(0, 3).join(", ")} and ${names.length - 3} more ${noun}`;
}

/** Announcement bodies come back as HTML (`<p>...</p>`); strips tags for a plain-text list
 * preview. Not used for the compose form - that still sends/shows the raw text as typed. */
export function stripHtml(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

/** The live API has no dedicated boolean "blocked" field — access is controlled by a
 * `status` string (confirmed values seen so far: "active"). This checks an explicit
 * blocked/is_blocked boolean first (in case that's ever added), then falls back to reading
 * status for anything that reads as blocked/suspended/banned/disabled. */
export function isBlockedUser(user: AnyRecord | null | undefined): boolean {
  const explicit = firstOfBool(user, ["blocked", "is_blocked"]);
  if (explicit !== undefined) return explicit;
  const status = firstOfString(user, ["status"], "active").toLowerCase();
  return /block|suspend|ban|disable/.test(status);
}
