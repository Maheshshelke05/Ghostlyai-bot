/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      // iOS system palette + the GhostlyAI orange as the tint colour
      colors: {
        brand: "#EA580C",
        "brand-ink": "#FFFFFF",
        "brand-soft": "#FFF1E8",
        go: "#34C759",
        ink: "#1C1C1E",
        muted: "#8E8E93",
        surface: "#FFFFFF",
        background: "#F2F2F7",
        line: "#E5E5EA",
        info: "#007AFF",
        danger: "#FF3B30",
      },
      fontFamily: {
        display: ["Baloo2_800ExtraBold"],
        heading: ["Baloo2_700Bold"],
        body: ["Mukta_400Regular"],
        "body-strong": ["Mukta_600SemiBold"],
      },
    },
  },
  plugins: [],
};
