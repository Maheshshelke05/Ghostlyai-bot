/** Design tokens (Chapter 14). Mirrors tailwind.config.js colors for use in JS
 * (icons, charts, native components that can't take a className). */
export const colors = {
  light: {
    brand: "#F8CB46",
    brandInk: "#2A2000",
    go: "#0C831F",
    ink: "#1E2420",
    muted: "#59615B",
    surface: "#FFFFFF",
    background: "#F4F5F0",
    line: "#DDE1D8",
    info: "#1F8FC7",
    danger: "#B3261E",
  },
  dark: {
    brand: "#F8CB46",
    brandInk: "#2A2000",
    go: "#4CC766",
    ink: "#E9ECE6",
    muted: "#A3ABA4",
    surface: "#1C221D",
    background: "#121612",
    line: "#2E362F",
    info: "#5CB8E6",
    danger: "#FF8A80",
  },
} as const;

export type ThemeColors = typeof colors.light;

export const spacing = [4, 8, 12, 16, 20, 24, 32] as const;

export const radii = {
  chip: 999,
  button: 14,
  card: 18,
  sheet: 24,
} as const;

export const statusColor = {
  paid: colors.light.go,
  trial: colors.light.info,
  expired: colors.light.muted,
  blocked: colors.light.danger,
  active: colors.light.go,
} as const;

export type AccessStatus = keyof typeof statusColor;
