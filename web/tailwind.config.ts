import type { Config } from "tailwindcss";

// Semantic tokens are defined as CSS variables in styles/tokens.css and surfaced
// here so utilities like `text-allow` / `bg-panel` map to the design direction.
const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        panel: "var(--panel)",
        "panel-2": "var(--panel-2)",
        border: "var(--border)",
        fg: "var(--fg)",
        muted: "var(--muted)",
        allow: "var(--allow)",
        deny: "var(--deny)",
        warn: "var(--warn)",
        info: "var(--info)",
        accent: "var(--accent)",
      },
      fontFamily: {
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
