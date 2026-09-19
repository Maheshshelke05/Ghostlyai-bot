/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      // JobKatta brand: a fresh green identity distinct from the admin app's orange, on the
      // same neutral iOS-system base so both apps share a visual "family" without twinning.
      colors: {
        brand: "#16A34A",
        "brand-ink": "#FFFFFF",
        "brand-soft": "#ECFDF3",
        accent: "#F59E0B",
        "accent-soft": "#FFFBEB",
        ink: "#1C1C1E",
        muted: "#8E8E93",
        surface: "#FFFFFF",
        background: "#F2F2F7",
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
