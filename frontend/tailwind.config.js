/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'primary-red': '#e63946',
        'secondary-red': '#d90429',
        'background-white': '#f1faee',
        'card-white': '#ffffff',
        'primary-text': '#1d3557',
        'secondary-text': '#457b9d',
        'border-color': '#e0e0e0',
      }
    },
  },
  plugins: [],
}