/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: { primary: 'var(--bg-primary)', secondary: 'var(--bg-secondary)', tertiary: 'var(--bg-tertiary)' },
        line: 'var(--border)',
        green: { 400: 'var(--green-400)', 500: 'var(--green-500)', 600: 'var(--green-600)' },
        red: { 400: 'var(--red-400)' },
        amber: { 400: 'var(--amber-400)' },
        blue: { 400: 'var(--blue-400)' },
        text: { primary: 'var(--text-primary)', secondary: 'var(--text-secondary)', muted: 'var(--text-muted)' },
      },
      fontFamily: { sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'], mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'] },
    },
  },
  plugins: [],
};
