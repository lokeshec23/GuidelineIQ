/** @type {import('tailwindcss').Config} */
const defaultTheme = require("tailwindcss/defaultTheme"); // ✅ Import defaultTheme

module.exports = {
  darkMode: 'class',
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      // ✅ DEFINE FONT FAMILIES
      fontFamily: {
        // 'sans' will be the default font for the entire application
        sans: ["Inter", ...defaultTheme.fontFamily.sans],
        // 'poppins' can be used for headings or specific elements
        poppins: ["Poppins", ...defaultTheme.fontFamily.sans],
      },
      colors: {
        base: "var(--bg-base)",
        surface: "var(--bg-surface)",
        accent: "var(--color-accent)",
        success: "var(--color-success)",
        "text-primary": "var(--text-primary)",
        "text-secondary": "var(--text-secondary)",
        primary: "var(--color-accent)", // Update to our accent
        secondary: "var(--color-success)", // Update to our success
      },
    },
  },
  plugins: [],
  corePlugins: {
    preflight: false, // Keep this disabled for Ant Design compatibility
  },
};
