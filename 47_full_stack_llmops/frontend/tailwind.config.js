/** @type {import('tailwindcss').Config} */
// 对应文章第 47 篇 —— Tailwind 工具类。
export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: '#4f46e5', dark: '#4338ca' },
      },
    },
  },
  plugins: [],
}
