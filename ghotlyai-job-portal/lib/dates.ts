/** Shared date helpers - always explicit about IST (+05:30), since JS otherwise interprets a
 * bare "YYYY-MM-DD" using the device's own timezone, which silently gives the wrong "days
 * left"/date on a phone not set to Indian time even though the backend always computes in IST
 * (CLAUDE.md: datetimes always displayed in IST, DD-MM-YYYY). */

export function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const diffMs = new Date(`${dateStr}T23:59:59+05:30`).getTime() - Date.now();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

export function formatDateDDMMYYYY(dateStr: string | null): string | null {
  if (!dateStr) return null;
  const [year, month, day] = dateStr.split("-");
  if (!year || !month || !day) return dateStr;
  return `${day}-${month}-${year}`;
}
