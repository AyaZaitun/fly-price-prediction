/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      boxShadow: {
        soft: '0 18px 40px rgba(15, 23, 42, 0.08)',
      },
      colors: {
        brand: {
          50: '#eef4ff',
          100: '#dfeaff',
          500: '#4f6ef7',
          600: '#4059d6',
          700: '#2f46a9',
        },
      },
    },
  },
  plugins: [],
};
