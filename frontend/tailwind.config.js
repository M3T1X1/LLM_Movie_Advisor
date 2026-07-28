/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#0b0b0a',
          900: '#11110f',
          850: '#171714',
          800: '#20201c',
        },
        slate: {
          50: '#f8f6f1',
          100: '#ece8df',
          200: '#d9d3c8',
          300: '#c2baae',
          400: '#aaa196',
          500: '#9a9288',
          600: '#8b847b',
          700: '#858078',
          800: '#393734',
          900: '#211f1d',
          950: '#12110f',
        },
        violet: {
          50: '#fff4ef',
          100: '#ffe2d8',
          200: '#ffc7b7',
          300: '#ffa18a',
          400: '#f57559',
          500: '#ce4028',
          600: '#b83220',
          700: '#9f2d1e',
          800: '#81271e',
          900: '#6a251e',
          950: '#39110c',
        },
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(245, 117, 89, 0.15)',
        card: '0 18px 50px rgba(0, 0, 0, 0.3)',
      },
      borderRadius: {
        md: '3px',
        lg: '5px',
        xl: '8px',
        '2xl': '10px',
      },
    },
  },
  plugins: [],
};
