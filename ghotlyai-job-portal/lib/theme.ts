/** Design tokens. Mirrors tailwind.config.js colors for use in JS (icons, native components
 * that can't take a className). Keep in sync with tailwind.config.js by hand - NativeWind
 * can't export its config back into JS. */
export const colors = {
  brand: "#16A34A",
  brandInk: "#FFFFFF",
  brandSoft: "#ECFDF3",
  accent: "#F59E0B",
  ink: "#1C1C1E",
  muted: "#8E8E93",
  surface: "#FFFFFF",
  background: "#F2F2F7",
  line: "#E5E5EA",
  info: "#007AFF",
  danger: "#FF3B30",
} as const;

export const statusColor = {
  paid: colors.brand,
  trial: colors.info,
  expired: colors.muted,
  blocked: colors.danger,
} as const;
