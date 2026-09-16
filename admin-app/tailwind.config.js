/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        brand: "#F8CB46",
        "brand-ink": "#2A2000",
        go: "#0C831F",
        ink: "#1E2420",
        muted: "#59615B",
        surface: "#FFFFFF",
        background: "#F4F5F0",
        line: "#DDE1D8",
        info: "#1F8FC7",
        danger: "#B3261E",
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
