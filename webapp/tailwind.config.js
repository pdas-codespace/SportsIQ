/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          gold:   "#F5A623",  // Electric amber
          navy:   "#1A3350",  // Medium stadium navy (cards)
          dark:   "#0F1F35",  // Page background navy
          field:  "#0D4A25",  // Deep emerald field green
          grass:  "#16A34A",  // Active/success green
          steel:  "#1E3D5C",  // Steel surface
          red:    "#DC2626",  // Energy red
          orange: "#EA580C",  // Hot orange
          lime:   "#22C55E",  // Bright success
          chalk:  "#E2E8F0",  // Yard-line white
        },
      },
      fontFamily: {
        display: ["'Oswald'", "sans-serif"],
      },
      backgroundImage: {
        "field-lines":
          "repeating-linear-gradient(90deg, transparent, transparent 49px, rgba(16,163,74,0.08) 50px)",
      },
      animation: {
        "pulse-fast": "pulse 0.8s cubic-bezier(0.4,0,0.6,1) infinite",
      },
    },
  },
  plugins: [],
};
