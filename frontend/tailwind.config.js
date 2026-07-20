/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#07080c',
          900: '#0c0e14',
          850: '#11141c',
          800: '#171a24',
        },
      },
      boxShadow: {
        glow: '0 0 40px rgba(139, 92, 246, 0.16)',
        card: '0 24px 70px rgba(0, 0, 0, 0.35)',
      },
    },
  },
  plugins: [],
};
