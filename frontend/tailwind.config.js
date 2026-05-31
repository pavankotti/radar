/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0a0a',
        surface: '#1c1c1c',
        accent: '#c7ff00',
        textPrimary: '#ffffff',
        textSecondary: '#a0a0a0'
      }
    },
  },
  plugins: [],
}
