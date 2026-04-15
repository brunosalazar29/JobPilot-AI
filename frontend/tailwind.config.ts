import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18212f",
        mist: "#f6f8fb",
        line: "#dce3ec",
        brand: "#1f766f",
        accent: "#d94f30"
      },
      boxShadow: {
        panel: "0 18px 45px rgba(24, 33, 47, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
