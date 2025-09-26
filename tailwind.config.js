/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
    './zargar/**/templates/**/*.html',
    './zargar/**/static/**/*.js',
    './node_modules/flowbite/**/*.js'
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // RTL-first font configuration
      fontFamily: {
        'vazir': ['Vazirmatn', 'Tahoma', 'Arial', 'sans-serif'],
        'yekan': ['Yekan Bakh', 'Vazirmatn', 'Tahoma', 'sans-serif'],
        'sans': ['Vazirmatn', 'system-ui', 'sans-serif'],
      },
      
      // Enhanced color palette for dual theme system
      colors: {
        // Light theme colors
        light: {
          'bg-primary': '#f9fafb',
          'bg-secondary': '#ffffff',
          'bg-surface': '#f3f4f6',
          'bg-elevated': '#e5e7eb',
          'text-primary': '#111827',
          'text-secondary': '#6b7280',
          'text-muted': '#9ca3af',
          'border': '#e5e7eb',
          'border-light': '#f3f4f6',
          'accent': '#3b82f6',
          'accent-hover': '#2563eb',
          'accent-light': '#dbeafe',
          'success': '#10b981',
          'warning': '#f59e0b',
          'error': '#ef4444',
        },
        
        // Cybersecurity theme colors
        cyber: {
          'bg-primary': '#0B0E1A',
          'bg-secondary': '#1A1D29',
          'bg-surface': '#252A3A',
          'bg-elevated': '#2D3348',
          'bg-glass': 'rgba(255, 255, 255, 0.03)',
          'bg-glass-hover': 'rgba(255, 255, 255, 0.05)',
          'neon-primary': '#00D4FF',
          'neon-secondary': '#00FF88',
          'neon-tertiary': '#FF6B35',
          'neon-warning': '#FFB800',
          'neon-danger': '#FF4757',
          'neon-success': '#00FF88',
          'neon-purple': '#A55EEA',
          'text-primary': '#FFFFFF',
          'text-secondary': '#B8BCC8',
          'text-muted': '#6B7280',
          'text-neon': '#00D4FF',
          'text-numbers': '#00FF88',
          'border-glass': 'rgba(255, 255, 255, 0.06)',
          'border-neon': 'rgba(0, 212, 255, 0.2)',
          'border-neon-hover': 'rgba(0, 212, 255, 0.4)',
        },
        
        // Persian-specific colors
        persian: {
          'gold': '#FFD700',
          'gold-dark': '#B8860B',
          'emerald': '#50C878',
          'ruby': '#E0115F',
          'sapphire': '#0F52BA',
        }
      },
      
      // RTL-aware spacing
      spacing: {
        'rtl-1': '0.25rem',
        'rtl-2': '0.5rem',
        'rtl-3': '0.75rem',
        'rtl-4': '1rem',
        'rtl-5': '1.25rem',
        'rtl-6': '1.5rem',
        'rtl-8': '2rem',
        'rtl-10': '2.5rem',
        'rtl-12': '3rem',
        'rtl-16': '4rem',
        'rtl-20': '5rem',
        'rtl-24': '6rem',
        'rtl-32': '8rem',
      },
      
      // Enhanced animations for cybersecurity theme
      animation: {
        'neon-pulse': 'neon-pulse 2s ease-in-out infinite alternate',
        'cyber-glow': 'cyber-glow 3s ease-in-out infinite',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
        'slide-in-left': 'slide-in-left 0.3s ease-out',
        'slide-out-right': 'slide-out-right 0.3s ease-in',
        'slide-out-left': 'slide-out-left 0.3s ease-in',
        'fade-in-up': 'fade-in-up 0.4s ease-out',
        'fade-in-down': 'fade-in-down 0.4s ease-out',
        'scale-in': 'scale-in 0.2s ease-out',
        'scale-out': 'scale-out 0.2s ease-in',
        'bounce-subtle': 'bounce-subtle 0.6s ease-in-out',
        'float': 'float 3s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'typing': 'typing 3.5s steps(40, end), blink-caret 0.75s step-end infinite',
      },
      
      keyframes: {
        'neon-pulse': {
          'from': { 
            boxShadow: '0 0 20px rgba(0, 212, 255, 0.1), 0 0 40px rgba(0, 212, 255, 0.05)' 
          },
          'to': { 
            boxShadow: '0 0 30px rgba(0, 212, 255, 0.3), 0 0 60px rgba(0, 255, 136, 0.1), 0 0 80px rgba(255, 107, 53, 0.05)' 
          }
        },
        'cyber-glow': {
          '0%, 100%': { 
            textShadow: '0 0 5px #00D4FF, 0 0 10px #00D4FF' 
          },
          '50%': { 
            textShadow: '0 0 10px #00D4FF, 0 0 20px #00D4FF, 0 0 30px #00D4FF, 0 0 40px #00D4FF' 
          }
        },
        'slide-in-right': {
          'from': { transform: 'translateX(100%)', opacity: '0' },
          'to': { transform: 'translateX(0)', opacity: '1' }
        },
        'slide-in-left': {
          'from': { transform: 'translateX(-100%)', opacity: '0' },
          'to': { transform: 'translateX(0)', opacity: '1' }
        },
        'slide-out-right': {
          'from': { transform: 'translateX(0)', opacity: '1' },
          'to': { transform: 'translateX(100%)', opacity: '0' }
        },
        'slide-out-left': {
          'from': { transform: 'translateX(0)', opacity: '1' },
          'to': { transform: 'translateX(-100%)', opacity: '0' }
        },
        'fade-in-up': {
          'from': { transform: 'translateY(20px)', opacity: '0' },
          'to': { transform: 'translateY(0)', opacity: '1' }
        },
        'fade-in-down': {
          'from': { transform: 'translateY(-20px)', opacity: '0' },
          'to': { transform: 'translateY(0)', opacity: '1' }
        },
        'scale-in': {
          'from': { transform: 'scale(0.95)', opacity: '0' },
          'to': { transform: 'scale(1)', opacity: '1' }
        },
        'scale-out': {
          'from': { transform: 'scale(1)', opacity: '1' },
          'to': { transform: 'scale(0.95)', opacity: '0' }
        },
        'bounce-subtle': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' }
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' }
        },
        'shimmer': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' }
        },
        'typing': {
          'from': { width: '0' },
          'to': { width: '100%' }
        },
        'blink-caret': {
          'from, to': { borderColor: 'transparent' },
          '50%': { borderColor: '#00D4FF' }
        }
      },
      
      // Enhanced backdrop blur
      backdropBlur: {
        'xs': '2px',
        'sm': '4px',
        'md': '8px',
        'lg': '16px',
        'xl': '24px',
        '2xl': '40px',
        '3xl': '64px',
      },
      
      // Enhanced box shadows for glassmorphism
      boxShadow: {
        'cyber': '0 12px 40px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.03)',
        'cyber-hover': '0 16px 50px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        'cyber-active': '0 8px 25px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.02)',
        'neon': '0 8px 32px rgba(0, 212, 255, 0.15), 0 0 20px rgba(0, 212, 255, 0.1)',
        'neon-hover': '0 12px 40px rgba(0, 212, 255, 0.25), 0 0 30px rgba(0, 212, 255, 0.2)',
        'neon-active': '0 4px 20px rgba(0, 212, 255, 0.3), 0 0 15px rgba(0, 212, 255, 0.15)',
        'glass': '0 8px 32px rgba(31, 38, 135, 0.37)',
        'glass-hover': '0 12px 40px rgba(31, 38, 135, 0.5)',
        'light-soft': '0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.06)',
        'light-medium': '0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.06)',
        'light-strong': '0 8px 24px rgba(0, 0, 0, 0.12), 0 4px 8px rgba(0, 0, 0, 0.08)',
      },
      
      // RTL-aware border radius
      borderRadius: {
        'rtl-sm': '0.125rem',
        'rtl': '0.25rem',
        'rtl-md': '0.375rem',
        'rtl-lg': '0.5rem',
        'rtl-xl': '0.75rem',
        'rtl-2xl': '1rem',
        'rtl-3xl': '1.5rem',
      },
      
      // Typography enhancements for Persian text
      fontSize: {
        'persian-xs': ['0.75rem', { lineHeight: '1.5', letterSpacing: '0.025em' }],
        'persian-sm': ['0.875rem', { lineHeight: '1.6', letterSpacing: '0.025em' }],
        'persian-base': ['1rem', { lineHeight: '1.7', letterSpacing: '0.025em' }],
        'persian-lg': ['1.125rem', { lineHeight: '1.7', letterSpacing: '0.025em' }],
        'persian-xl': ['1.25rem', { lineHeight: '1.7', letterSpacing: '0.025em' }],
        'persian-2xl': ['1.5rem', { lineHeight: '1.6', letterSpacing: '0.025em' }],
        'persian-3xl': ['1.875rem', { lineHeight: '1.5', letterSpacing: '0.025em' }],
        'persian-4xl': ['2.25rem', { lineHeight: '1.4', letterSpacing: '0.025em' }],
      },
      
      // Enhanced line heights for Persian text
      lineHeight: {
        'persian-tight': '1.4',
        'persian-normal': '1.6',
        'persian-relaxed': '1.8',
        'persian-loose': '2.0',
      },
      
      // Enhanced letter spacing for Persian text
      letterSpacing: {
        'persian-tighter': '-0.025em',
        'persian-tight': '-0.0125em',
        'persian-normal': '0em',
        'persian-wide': '0.025em',
        'persian-wider': '0.05em',
        'persian-widest': '0.1em',
      },
      
      // Enhanced z-index scale
      zIndex: {
        'dropdown': '1000',
        'sticky': '1020',
        'fixed': '1030',
        'modal-backdrop': '1040',
        'modal': '1050',
        'popover': '1060',
        'tooltip': '1070',
        'toast': '1080',
      },
      
      // Enhanced transition durations
      transitionDuration: {
        '50': '50ms',
        '100': '100ms',
        '200': '200ms',
        '250': '250ms',
        '400': '400ms',
        '500': '500ms',
        '600': '600ms',
        '700': '700ms',
        '800': '800ms',
        '900': '900ms',
        '1000': '1000ms',
      },
      
      // Enhanced transition timing functions
      transitionTimingFunction: {
        'bounce-in': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'bounce-out': 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
        'smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'smooth-in': 'cubic-bezier(0.4, 0, 1, 1)',
        'smooth-out': 'cubic-bezier(0, 0, 0.2, 1)',
      }
    },
  },
  plugins: [
    require('flowbite/plugin'),
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
    
    // Custom RTL plugin
    function({ addUtilities, addComponents, theme }) {
      // RTL utilities
      addUtilities({
        '.rtl-flip': {
          transform: 'scaleX(-1)',
        },
        '.ltr-content': {
          direction: 'ltr',
          textAlign: 'left',
        },
        '.rtl-content': {
          direction: 'rtl',
          textAlign: 'right',
        },
        '.persian-numbers': {
          fontFeatureSettings: '"lnum" 1',
          direction: 'ltr',
          display: 'inline-block',
          textAlign: 'right',
        },
        '.persian-text': {
          fontFamily: theme('fontFamily.vazir'),
          direction: 'rtl',
          textAlign: 'right',
        },
        '.cyber-text-glow': {
          textShadow: '0 0 10px theme("colors.cyber.neon-primary")',
        },
        '.cyber-number-glow': {
          color: theme('colors.cyber.neon-secondary'),
          textShadow: '0 0 8px rgba(0, 255, 136, 0.3)',
          fontWeight: '600',
        },
      });
      
      // RTL-aware components
      addComponents({
        '.cyber-glass-card': {
          backdropFilter: 'blur(16px) saturate(150%)',
          background: 'linear-gradient(145deg, rgba(37, 42, 58, 0.8) 0%, rgba(26, 29, 41, 0.9) 50%, rgba(11, 14, 26, 0.95) 100%)',
          border: `1px solid ${theme('colors.cyber.border-glass')}`,
          boxShadow: theme('boxShadow.cyber'),
          borderRadius: theme('borderRadius.xl'),
          transition: 'all 0.3s ease',
          position: 'relative',
          overflow: 'hidden',
          
          '&::before': {
            content: '""',
            position: 'absolute',
            top: '0',
            left: '0',
            right: '0',
            height: '1px',
            background: `linear-gradient(90deg, transparent, ${theme('colors.cyber.neon-primary')}, transparent)`,
            opacity: '0.3',
          },
          
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: theme('boxShadow.cyber-hover'),
            borderColor: theme('colors.cyber.border-neon-hover'),
          }
        },
        
        '.cyber-neon-button': {
          background: `linear-gradient(145deg, rgba(0, 212, 255, 0.08) 0%, rgba(0, 255, 136, 0.04) 100%)`,
          border: `1px solid ${theme('colors.cyber.border-neon')}`,
          boxShadow: theme('boxShadow.neon'),
          color: theme('colors.cyber.text-primary'),
          padding: `${theme('spacing.3')} ${theme('spacing.6')}`,
          borderRadius: theme('borderRadius.lg'),
          fontWeight: '500',
          transition: 'all 0.3s ease',
          cursor: 'pointer',
          position: 'relative',
          overflow: 'hidden',
          
          '&::before': {
            content: '""',
            position: 'absolute',
            top: '0',
            left: '-100%',
            width: '100%',
            height: '100%',
            background: 'linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.2), transparent)',
            transition: 'left 0.5s ease',
          },
          
          '&:hover::before': {
            left: '100%',
          },
          
          '&:hover': {
            transform: 'scale(1.05)',
            boxShadow: theme('boxShadow.neon-hover'),
            borderColor: theme('colors.cyber.border-neon-hover'),
          },
          
          '&:active': {
            transform: 'scale(0.98)',
            boxShadow: theme('boxShadow.neon-active'),
          }
        },
        
        '.light-card': {
          backgroundColor: theme('colors.light.bg-secondary'),
          border: `1px solid ${theme('colors.light.border')}`,
          boxShadow: theme('boxShadow.light-soft'),
          borderRadius: theme('borderRadius.lg'),
          transition: 'all 0.3s ease',
          
          '&:hover': {
            boxShadow: theme('boxShadow.light-medium'),
            transform: 'translateY(-2px)',
          }
        },
        
        '.light-button': {
          backgroundColor: theme('colors.light.accent'),
          color: 'white',
          border: 'none',
          padding: `${theme('spacing.3')} ${theme('spacing.6')}`,
          borderRadius: theme('borderRadius.lg'),
          fontWeight: '500',
          transition: 'all 0.3s ease',
          cursor: 'pointer',
          
          '&:hover': {
            backgroundColor: theme('colors.light.accent-hover'),
            transform: 'translateY(-1px)',
            boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)',
          },
          
          '&:active': {
            transform: 'translateY(0)',
          }
        },
        
        '.persian-input': {
          fontFamily: theme('fontFamily.vazir'),
          direction: 'rtl',
          textAlign: 'right',
          padding: `${theme('spacing.3')} ${theme('spacing.4')}`,
          borderRadius: theme('borderRadius.lg'),
          transition: 'all 0.3s ease',
          
          '&:focus': {
            outline: 'none',
            boxShadow: `0 0 0 3px ${theme('colors.light.accent')}33`,
          },
          
          '&.dark': {
            backgroundColor: theme('colors.cyber.bg-surface'),
            border: `1px solid ${theme('colors.cyber.border-glass')}`,
            color: theme('colors.cyber.text-primary'),
            
            '&:focus': {
              borderColor: theme('colors.cyber.neon-primary'),
              boxShadow: `0 0 0 3px ${theme('colors.cyber.neon-primary')}33`,
            }
          }
        }
      });
    }
  ],
}