/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        serif: ['Instrument Serif', 'Georgia', 'serif'],
        sans: ['Manrope', 'system-ui', 'sans-serif'],
        mono: ['DM Mono', 'JetBrains Mono', 'monospace'],
      },
      colors: {
        coral: {
          DEFAULT: '#EF4623',
          50: '#FDF1EE',
          100: '#FBE4DE',
          200: '#F7C9BD',
          300: '#F3AE9C',
          400: '#EF937B',
          500: '#EF4623',
          600: '#D93418',
          700: '#B02914',
          800: '#871F10',
          900: '#5E140C',
        },
        ink: {
          DEFAULT: '#2D3B42',
          50: '#E8ECEE',
          100: '#D1D9DD',
          200: '#A3B3BC',
          300: '#758D9B',
          400: '#47677A',
          500: '#2D3B42',
          600: '#273338',
          700: '#1F292F',
          800: '#171F25',
          900: '#0F151B',
        },
        peach: {
          DEFAULT: '#FDF1EE',
          light: '#FEF6F3',
        },
      },
      animation: {
        'fade-up': 'fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'fade-in': 'fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-in': 'slideIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'rotate-logo': 'rotateLogo 0.3s ease forwards',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(20px) rotate(2deg)' },
          '100%': { opacity: '1', transform: 'translateY(0) rotate(0deg)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { opacity: '0', transform: 'translateX(-10px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        rotateLogo: {
          '0%': { transform: 'rotate(3deg)' },
          '100%': { transform: 'rotate(12deg)' },
        },
      },
      boxShadow: {
        'coral-lg': '0 10px 40px -10px rgba(239, 70, 35, 0.25)',
        'coral-sm': '0 4px 12px -2px rgba(239, 70, 35, 0.2)',
        'glass': '0 8px 32px rgba(31, 41, 47, 0.1)',
      },
      backdropBlur: {
        'glass': '12px',
      },
      borderRadius: {
        '3xl': '1.5rem',
        '4xl': '2rem',
        '5xl': '3rem',
      },
    },
  },
  plugins: [],
}
