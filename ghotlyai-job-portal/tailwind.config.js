/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      // Same GhotlyAI brand as the admin app (ghost mascot + orange), on a white-forward
      // background per an explicit request to keep the app's own screens clean/white while
      // the app icon keeps the recognizable orange ghost mark.
      colors: {
        brand: "#EA580C",
        "brand-ink": "#FFFFFF",
        "brand-soft": "#FFF1E8",
        accent: "#F59E0B",
        "accent-soft": "#FFFBEB",
        ink: "#1C1C1E",
        muted: "#8E8E93",
        surface: "#FFFFFF",
        background: "#FFFFFF",
        line: "#E5E5EA",
        info: "#007AFF",
        danger: "#FF3B30",
      },
      fontFamily: {
        display: ["Poppins_700Bold"],
        heading: ["Poppins_600SemiBold"],
        body: ["Hind_400Regular"],
        "body-strong": ["Hind_600SemiBold"],
      },
    },
  },
  plugins: [],
};
