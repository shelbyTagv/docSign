/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f4f8',
          100: '#dbe5f0',
          200: '#bcd0e2',
          300: '#8eb1d0',
          400: '#598cb8',
          500: '#386fa4',
          600: '#2a5784',
          700: '#22476b',
          800: '#1e3a57', // Primary navy blue
          900: '#1d334a',
          950: '#132132',
        },
      },
    },
  },
  plugins: [],
}
