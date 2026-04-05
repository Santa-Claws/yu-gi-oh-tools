import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Yu-Gi-Oh-inspired palette
        spell: "#1d8348",
        trap: "#922b21",
        monster: "#d4ac0d",
        link: "#1a5276",
        xyz: "#1c1c1c",
        synchro: "#f8f9fa",
        fusion: "#6c3483",
        ritual: "#154360",
      },
    },
  },
  plugins: [],
};

export default config;
