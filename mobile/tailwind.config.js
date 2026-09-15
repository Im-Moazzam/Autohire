/** Same source of truth as frontend/src/styles/tokens.css and docs/design.md —
 * keep these two in sync by hand until there's a shared tokens package. */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  // "media" (the default) crashes react-native-css-interop's web runtime the
  // moment anything touches Appearance — the app doesn't offer a dark theme
  // yet anyway, so "class" (opt-in only) sidesteps it.
  darkMode: "class",
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: "#0058BE",
        navy: "#0F172A",
        "primary-soft": "#D8E2FF",
        cyan: "#06B6D4",
        ai: "#7C3AED",
        success: "#16A34A",
        warning: "#F59E0B",
        error: "#DC2626",
        canvas: "#F8FAFC",
        surface: "#FFFFFF",
        border: "#E2E8F0",
        muted: "#64748B",
        ink: "#0F172A",
      },
      borderRadius: {
        sm: "4px",
        control: "8px",
        card: "16px",
        xl: "24px",
      },
      fontSize: {
        page: "28px",
        section: "20px",
        card: "17px",
        body: "16px",
        table: "14px",
        helper: "13px",
      },
    },
  },
  plugins: [],
};
