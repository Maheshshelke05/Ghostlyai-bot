/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      // Same GhotlyAI brand as the admin app (ghost mascot + orange) - the orange stays as
      // the one accent color (buttons, highlights), but the backdrop is a soft warm cream
      // instead of stark white, with white cards on top, for a calmer "premium fintech" feel.
      colors: {
        brand: "#EA580C",
        "brand-ink": "#FFFFFF",
        "brand-soft": "#FFF1E8",
        accent: "#F59E0B",
        "accent-soft": "#FFFBEB",
        ink: "#1C1C1E",
        muted: "#8E8E93",
        surface: "#FFFFFF",
        background: "#F7F5F2",
        line: "#E9E6E1",
        info: "#007AFF",
        danger: "#FF3B30",
      },
      fontFamily: {
        // Serif display for large headlines/numbers (profile name, prices, screen titles),
        // sans-serif Poppins for smaller section headings - mirrors the editorial serif +
        // clean-sans mix of the reference design.
        display: ["Newsreader_700Bold"],
        heading: ["Poppins_600SemiBold"],
        body: ["Hind_400Regular"],
        "body-strong": ["Hind_600SemiBold"],
      },
    },
  },
  plugins: [],
};
