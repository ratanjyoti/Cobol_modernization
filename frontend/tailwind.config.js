/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // This is the magic line
  theme: {
    extend: {
      colors: {
        // We define "Semantic Colors" that change based on the theme
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6', // Primary Blue
          600: '#2563eb',
          700: '#1d4ed8',
        },
        surface: {
          light: '#ffffff',
          dark: '#0f172a',
        }
      },
    },
  },
  plugins: [],
}
