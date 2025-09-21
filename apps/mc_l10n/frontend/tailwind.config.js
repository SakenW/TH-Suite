/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    './src/**/*.{css,scss}',
  ],
  darkMode: ['class', 'class'],
  theme: {
  	extend: {
  		// ===== 三层Token系统集成 =====
  		// Core Tokens - 基础设计令牌
  		coreTokens: {
  			// 从CSS变量映射核心令牌
  			colors: {
  				primary: {
  					50: 'var(--core-color-primary-50)',
  					100: 'var(--core-color-primary-100)',
  					200: 'var(--core-color-primary-200)',
  					300: 'var(--core-color-primary-300)',
  					400: 'var(--core-color-primary-400)',
  					500: 'var(--core-color-primary-500)',
  					600: 'var(--core-color-primary-600)',
  					700: 'var(--core-color-primary-700)',
  					800: 'var(--core-color-primary-800)',
  					900: 'var(--core-color-primary-900)',
  				},
  				secondary: {
  					50: 'var(--core-color-secondary-50)',
  					100: 'var(--core-color-secondary-100)',
  					200: 'var(--core-color-secondary-200)',
  					300: 'var(--core-color-secondary-300)',
  					400: 'var(--core-color-secondary-400)',
  					500: 'var(--core-color-secondary-500)',
  					600: 'var(--core-color-secondary-600)',
  					700: 'var(--core-color-secondary-700)',
  					800: 'var(--core-color-secondary-800)',
  					900: 'var(--core-color-secondary-900)',
  				},
  				neutral: {
  					white: 'var(--core-color-neutral-white)',
  					50: 'var(--core-color-neutral-50)',
  					100: 'var(--core-color-neutral-100)',
  					200: 'var(--core-color-neutral-200)',
  					300: 'var(--core-color-neutral-300)',
  					400: 'var(--core-color-neutral-400)',
  					500: 'var(--core-color-neutral-500)',
  					600: 'var(--core-color-neutral-600)',
  					700: 'var(--core-color-neutral-700)',
  					800: 'var(--core-color-neutral-800)',
  					900: 'var(--core-color-neutral-900)',
  					black: 'var(--core-color-neutral-black)',
  				},
  				status: {
  					success: 'var(--core-color-success)',
  					warning: 'var(--core-color-warning)',
  					error: 'var(--core-color-error)',
  					info: 'var(--core-color-info)',
  					processing: 'var(--core-color-processing)',
  				},
  			},
  			spacing: {
  				0: 'var(--core-spacing-0)',
  				1: 'var(--core-spacing-1)',
  				2: 'var(--core-spacing-2)',
  				3: 'var(--core-spacing-3)',
  				4: 'var(--core-spacing-4)',
  				5: 'var(--core-spacing-5)',
  				6: 'var(--core-spacing-6)',
  				8: 'var(--core-spacing-8)',
  				10: 'var(--core-spacing-10)',
  				12: 'var(--core-spacing-12)',
  				16: 'var(--core-spacing-16)',
  				20: 'var(--core-spacing-20)',
  				24: 'var(--core-spacing-24)',
  				32: 'var(--core-spacing-32)',
  				40: 'var(--core-spacing-40)',
  				48: 'var(--core-spacing-48)',
  				56: 'var(--core-spacing-56)',
  				64: 'var(--core-spacing-64)',
  			},
  			borderRadius: {
  				none: 'var(--core-radius-none)',
  				sm: 'var(--core-radius-sm)',
  				base: 'var(--core-radius-base)',
  				md: 'var(--core-radius-md)',
  				lg: 'var(--core-radius-lg)',
  				xl: 'var(--core-radius-xl)',
  				'2xl': 'var(--core-radius-2xl)',
  				'3xl': 'var(--core-radius-3xl)',
  				full: 'var(--core-radius-full)',
  			},
  			fontSize: {
  				xs: 'var(--core-font-size-xs)',
  				sm: 'var(--core-font-size-sm)',
  				base: 'var(--core-font-size-base)',
  				lg: 'var(--core-font-size-lg)',
  				xl: 'var(--core-font-size-xl)',
  				'2xl': 'var(--core-font-size-2xl)',
  				'3xl': 'var(--core-font-size-3xl)',
  				'4xl': 'var(--core-font-size-4xl)',
  				'5xl': 'var(--core-font-size-5xl)',
  				'6xl': 'var(--core-font-size-6xl)',
  				'7xl': 'var(--core-font-size-7xl)',
  				'8xl': 'var(--core-font-size-8xl)',
  				'9xl': 'var(--core-font-size-9xl)',
  			},
  			boxShadow: {
  				sm: 'var(--core-shadow-sm)',
  				base: 'var(--core-shadow-base)',
  				md: 'var(--core-shadow-md)',
  				lg: 'var(--core-shadow-lg)',
  				xl: 'var(--core-shadow-xl)',
  				'2xl': 'var(--core-shadow-2xl)',
  				inner: 'var(--core-shadow-inner)',
  				none: 'var(--core-shadow-none)',
  			},
  		},

  		// Semantic Tokens - 语义化令牌
  		semanticTokens: {
  			colors: {
  				// 品牌色
  				brand: {
  					primary: 'var(--semantic-color-brand-primary)',
  					'primary-hover': 'var(--semantic-color-brand-primary-hover)',
  					'primary-active': 'var(--semantic-color-brand-primary-active)',
  					'primary-subtle': 'var(--semantic-color-brand-primary-subtle)',
  					secondary: 'var(--semantic-color-brand-secondary)',
  					'secondary-hover': 'var(--semantic-color-brand-secondary-hover)',
  					'secondary-active': 'var(--semantic-color-brand-secondary-active)',
  					'secondary-subtle': 'var(--semantic-color-brand-secondary-subtle)',
  				},
  				// 背景色
  				bg: {
  					base: 'var(--semantic-bg-base)',
  					elevated: 'var(--semantic-bg-elevated)',
  					sunken: 'var(--semantic-bg-sunken)',
  					surface: {
  						primary: 'var(--semantic-bg-surface-primary)',
  						secondary: 'var(--semantic-bg-surface-secondary)',
  						tertiary: 'var(--semantic-bg-surface-tertiary)',
  						inverse: 'var(--semantic-bg-surface-inverse)',
  					},
  					container: {
  						primary: 'var(--semantic-bg-container-primary)',
  						secondary: 'var(--semantic-bg-container-secondary)',
  						tertiary: 'var(--semantic-bg-container-tertiary)',
  						emphasis: 'var(--semantic-bg-container-emphasis)',
  					},
  					state: {
  						hover: 'var(--semantic-bg-hover)',
  						pressed: 'var(--semantic-bg-pressed)',
  						selected: 'var(--semantic-bg-selected)',
  						focus: 'var(--semantic-bg-focus)',
  						disabled: 'var(--semantic-bg-disabled)',
  					},
  				},
  				// 文本色
  				text: {
  					primary: 'var(--semantic-text-primary)',
  					secondary: 'var(--semantic-text-secondary)',
  					tertiary: 'var(--semantic-text-tertiary)',
  					quaternary: 'var(--semantic-text-quaternary)',
  					disabled: 'var(--semantic-text-disabled)',
  					inverse: {
  						primary: 'var(--semantic-text-inverse-primary)',
  						secondary: 'var(--semantic-text-inverse-secondary)',
  						tertiary: 'var(--semantic-text-inverse-tertiary)',
  						disabled: 'var(--semantic-text-inverse-disabled)',
  					},
  					link: {
  						default: 'var(--semantic-text-link)',
  						hover: 'var(--semantic-text-link-hover)',
  						active: 'var(--semantic-text-link-active)',
  						visited: 'var(--semantic-text-link-visited)',
  					},
  					status: {
  						success: 'var(--semantic-text-success)',
  						warning: 'var(--semantic-text-warning)',
  						error: 'var(--semantic-text-error)',
  						info: 'var(--semantic-text-info)',
  					},
  				},
  				// 边框色
  				border: {
  					primary: 'var(--semantic-border-primary)',
  					secondary: 'var(--semantic-border-secondary)',
  					tertiary: 'var(--semantic-border-tertiary)',
  					inverse: 'var(--semantic-border-inverse)',
  					interactive: {
  						hover: 'var(--semantic-border-hover)',
  						focus: 'var(--semantic-border-focus)',
  						active: 'var(--semantic-border-active)',
  						selected: 'var(--semantic-border-selected)',
  						disabled: 'var(--semantic-border-disabled)',
  					},
  					status: {
  						success: 'var(--semantic-border-success)',
  						warning: 'var(--semantic-border-warning)',
  						error: 'var(--semantic-border-error)',
  						info: 'var(--semantic-border-info)',
  					},
  				},
  			},
  			boxShadow: {
  				// 高度阴影
  				elevation: {
  					low: 'var(--semantic-shadow-elevation-low)',
  					medium: 'var(--semantic-shadow-elevation-medium)',
  					high: 'var(--semantic-shadow-elevation-high)',
  					highest: 'var(--semantic-shadow-elevation-highest)',
  				},
  				// 交互阴影
  				interactive: {
  					hover: 'var(--semantic-shadow-hover)',
  					active: 'var(--semantic-shadow-active)',
  					focus: 'var(--semantic-shadow-focus)',
  				},
  				// 组件阴影
  				component: {
  					card: 'var(--semantic-shadow-card)',
  					'card-hover': 'var(--semantic-shadow-card-hover)',
  					modal: 'var(--semantic-shadow-modal)',
  					dropdown: 'var(--semantic-shadow-dropdown)',
  					tooltip: 'var(--semantic-shadow-tooltip)',
  					popover: 'var(--semantic-shadow-popover)',
  				},
  				// Minecraft风格阴影
  				minecraft: {
  					pixel: 'var(--semantic-shadow-minecraft-pixel)',
  					block: 'var(--semantic-shadow-minecraft-block)',
  					glow: 'var(--semantic-shadow-minecraft-glow)',
  				},
  			},
  			spacing: {
  				layout: {
  					xs: 'var(--semantic-spacing-layout-xs)',
  					sm: 'var(--semantic-spacing-layout-sm)',
  					md: 'var(--semantic-spacing-layout-md)',
  					lg: 'var(--semantic-spacing-layout-lg)',
  					xl: 'var(--semantic-spacing-layout-xl)',
  				},
  				component: {
  					xs: 'var(--semantic-spacing-component-xs)',
  					sm: 'var(--semantic-spacing-component-sm)',
  					md: 'var(--semantic-spacing-component-md)',
  					lg: 'var(--semantic-spacing-component-lg)',
  					xl: 'var(--semantic-spacing-component-xl)',
  				},
  				content: {
  					xs: 'var(--semantic-spacing-content-xs)',
  					sm: 'var(--semantic-spacing-content-sm)',
  					md: 'var(--semantic-spacing-content-md)',
  					lg: 'var(--semantic-spacing-content-lg)',
  					xl: 'var(--semantic-spacing-content-xl)',
  				},
  			},
  			borderRadius: {
  				component: {
  					button: 'var(--semantic-radius-button)',
  					input: 'var(--semantic-radius-input)',
  					card: 'var(--semantic-radius-card)',
  					modal: 'var(--semantic-radius-modal)',
  					avatar: 'var(--semantic-radius-avatar)',
  					tag: 'var(--semantic-radius-tag)',
  				},
  			},
  			transitionDuration: {
  				instant: 'var(--semantic-duration-instant)',
  				fast: 'var(--semantic-duration-fast)',
  				normal: 'var(--semantic-duration-normal)',
  				slow: 'var(--semantic-duration-slow)',
  				slower: 'var(--semantic-duration-slower)',
  			},
  			zIndex: {
  				base: 'var(--semantic-z-index-base)',
  				dropdown: 'var(--semantic-z-index-dropdown)',
  				sticky: 'var(--semantic-z-index-sticky)',
  				modal: 'var(--semantic-z-index-modal)',
  				popover: 'var(--semantic-z-index-popover)',
  				tooltip: 'var(--semantic-z-index-tooltip)',
  				toast: 'var(--semantic-z-index-toast)',
  			},
  		},

  		// Component Tokens - 组件令牌
  		componentTokens: {
  			button: {
  				// 默认按钮
  				default: {
  					bg: 'var(--component-button-default-bg)',
  					border: 'var(--component-button-default-border)',
  					text: 'var(--component-button-default-text)',
  					shadow: 'var(--component-button-default-shadow)',
  					radius: 'var(--component-button-default-radius)',
  					height: 'var(--component-button-default-height)',
  					fontSize: 'var(--component-button-default-font-size)',
  					fontWeight: 'var(--component-button-default-font-weight)',
  					hover: {
  						bg: 'var(--component-button-default-hover-bg)',
  						border: 'var(--component-button-default-hover-border)',
  						shadow: 'var(--component-button-default-hover-shadow)',
  						transform: 'var(--component-button-default-hover-transform)',
  					},
  					active: {
  						bg: 'var(--component-button-default-active-bg)',
  						border: 'var(--component-button-default-active-border)',
  						shadow: 'var(--component-button-default-active-shadow)',
  						transform: 'var(--component-button-default-active-transform)',
  					},
  					focus: {
  						shadow: 'var(--component-button-default-focus-shadow)',
  						outline: 'var(--component-button-default-focus-outline)',
  						outlineOffset: 'var(--component-button-default-focus-outline-offset)',
  					},
  					disabled: {
  						bg: 'var(--component-button-default-disabled-bg)',
  						border: 'var(--component-button-default-disabled-border)',
  						text: 'var(--component-button-default-disabled-text)',
  						opacity: 'var(--component-button-default-disabled-opacity)',
  					},
  				},
  				// 主要按钮
  				primary: {
  					bg: 'var(--component-button-primary-bg)',
  					border: 'var(--component-button-primary-border)',
  					text: 'var(--component-button-primary-text)',
  					shadow: 'var(--component-button-primary-shadow)',
  					hover: {
  						bg: 'var(--component-button-primary-hover-bg)',
  						border: 'var(--component-button-primary-hover-border)',
  						shadow: 'var(--component-button-primary-hover-shadow)',
  						transform: 'var(--component-button-primary-hover-transform)',
  					},
  					active: {
  						bg: 'var(--component-button-primary-active-bg)',
  						border: 'var(--component-button-primary-active-border)',
  						shadow: 'var(--component-button-primary-active-shadow)',
  						transform: 'var(--component-button-primary-active-transform)',
  					},
  				},
  				// 次要按钮
  				secondary: {
  					bg: 'var(--component-button-secondary-bg)',
  					border: 'var(--component-button-secondary-border)',
  					text: 'var(--component-button-secondary-text)',
  					shadow: 'var(--component-button-secondary-shadow)',
  					hover: {
  						bg: 'var(--component-button-secondary-hover-bg)',
  						border: 'var(--component-button-secondary-hover-border)',
  						shadow: 'var(--component-button-secondary-hover-shadow)',
  					},
  				},
  				// 幽灵按钮
  				ghost: {
  					bg: 'var(--component-button-ghost-bg)',
  					border: 'var(--component-button-ghost-border)',
  					text: 'var(--component-button-ghost-text)',
  					shadow: 'var(--component-button-ghost-shadow)',
  					hover: {
  						bg: 'var(--component-button-ghost-hover-bg)',
  						border: 'var(--component-button-ghost-hover-border)',
  						text: 'var(--component-button-ghost-hover-text)',
  						transform: 'var(--component-button-ghost-hover-transform)',
  					},
  				},
  				// 文本按钮
  				text: {
  					bg: 'var(--component-button-text-bg)',
  					border: 'var(--component-button-text-border)',
  					text: 'var(--component-button-text-text)',
  					shadow: 'var(--component-button-text-shadow)',
  					hover: {
  						bg: 'var(--component-button-text-hover-bg)',
  						text: 'var(--component-button-text-hover-text)',
  					},
  				},
  				// 按钮尺寸
  				size: {
  					sm: {
  						height: 'var(--component-button-sm-height)',
  						paddingX: 'var(--component-button-sm-padding-x)',
  						paddingY: 'var(--component-button-sm-padding-y)',
  						fontSize: 'var(--component-button-sm-font-size)',
  					},
  					lg: {
  						height: 'var(--component-button-lg-height)',
  						paddingX: 'var(--component-button-lg-padding-x)',
  						paddingY: 'var(--component-button-lg-padding-y)',
  						fontSize: 'var(--component-button-lg-font-size)',
  					},
  					xl: {
  						height: 'var(--component-button-xl-height)',
  						paddingX: 'var(--component-button-xl-padding-x)',
  						paddingY: 'var(--component-button-xl-padding-y)',
  						fontSize: 'var(--component-button-xl-font-size)',
  					},
  				},
  			},
  			card: {
  				base: {
  					bg: 'var(--component-card-bg)',
  					border: 'var(--component-card-border)',
  					borderWidth: 'var(--component-card-border-width)',
  					radius: 'var(--component-card-radius)',
  					shadow: 'var(--component-card-shadow)',
  					padding: 'var(--component-card-padding)',
  					hover: {
  						bg: 'var(--component-card-hover-bg)',
  						border: 'var(--component-card-hover-border)',
  						shadow: 'var(--component-card-hover-shadow)',
  						transform: 'var(--component-card-hover-transform)',
  					},
  					active: {
  						bg: 'var(--component-card-active-bg)',
  						border: 'var(--component-card-active-border)',
  						shadow: 'var(--component-card-active-shadow)',
  					},
  				},
  				header: {
  					bg: 'var(--component-card-header-bg)',
  					border: 'var(--component-card-header-border)',
  					padding: 'var(--component-card-header-padding)',
  					text: 'var(--component-card-header-text)',
  					fontSize: 'var(--component-card-header-font-size)',
  					fontWeight: 'var(--component-card-header-font-weight)',
  				},
  				footer: {
  					bg: 'var(--component-card-footer-bg)',
  					border: 'var(--component-card-footer-border)',
  					padding: 'var(--component-card-footer-padding)',
  				},
  				variants: {
  					elevated: {
  						shadow: 'var(--component-card-elevated-shadow)',
  					},
  					outlined: {
  						border: 'var(--component-card-outlined-border)',
  					},
  					filled: {
  						bg: 'var(--component-card-filled-bg)',
  					},
  				},
  			},
  			input: {
  				base: {
  					bg: 'var(--component-input-bg)',
  					border: 'var(--component-input-border)',
  					borderWidth: 'var(--component-input-border-width)',
  					radius: 'var(--component-input-radius)',
  					paddingX: 'var(--component-input-padding-x)',
  					paddingY: 'var(--component-input-padding-y)',
  					height: 'var(--component-input-height)',
  					fontSize: 'var(--component-input-font-size)',
  					text: 'var(--component-input-text)',
  					placeholder: 'var(--component-input-placeholder)',
  					hover: {
  						border: 'var(--component-input-hover-border)',
  						bg: 'var(--component-input-hover-bg)',
  					},
  					focus: {
  						border: 'var(--component-input-focus-border)',
  						shadow: 'var(--component-input-focus-shadow)',
  						outline: 'var(--component-input-focus-outline)',
  					},
  					active: {
  						border: 'var(--component-input-active-border)',
  						bg: 'var(--component-input-active-bg)',
  					},
  					disabled: {
  						bg: 'var(--component-input-disabled-bg)',
  						border: 'var(--component-input-disabled-border)',
  						text: 'var(--component-input-disabled-text)',
  						opacity: 'var(--component-input-disabled-opacity)',
  					},
  				},
  				status: {
  					error: {
  						border: 'var(--component-input-error-border)',
  						shadow: 'var(--component-input-error-shadow)',
  						bg: 'var(--component-input-error-bg)',
  					},
  					success: {
  						border: 'var(--component-input-success-border)',
  						shadow: 'var(--component-input-success-shadow)',
  						bg: 'var(--component-input-success-bg)',
  					},
  					warning: {
  						border: 'var(--component-input-warning-border)',
  						shadow: 'var(--component-input-warning-shadow)',
  						bg: 'var(--component-input-warning-bg)',
  					},
  				},
  				size: {
  					sm: {
  						height: 'var(--component-input-sm-height)',
  						paddingX: 'var(--component-input-sm-padding-x)',
  						paddingY: 'var(--component-input-sm-padding-y)',
  						fontSize: 'var(--component-input-sm-font-size)',
  					},
  					lg: {
  						height: 'var(--component-input-lg-height)',
  						paddingX: 'var(--component-input-lg-padding-x)',
  						paddingY: 'var(--component-input-lg-padding-y)',
  						fontSize: 'var(--component-input-lg-font-size)',
  					},
  				},
  			},
  			// 其他组件令牌...
  		},

  		// 保持原有配置兼容性
  		// 兼容性颜色配置（向后兼容）
  		colors: {
  			primary: {
  				'50': '#e6f4ff',
  				'100': '#bae0ff',
  				'500': '#1677ff',
  				'600': '#0958d9',
  				'700': '#003eb3'
  			},
  			gray: {
  				'50': '#fafafa',
  				'100': '#f5f5f5',
  				'200': '#f0f0f0',
  				'300': '#d9d9d9',
  				'400': '#bfbfbf',
  				'500': '#8c8c8c',
  				'600': '#595959',
  				'700': '#434343',
  				'800': '#262626',
  				'900': '#1f1f1f'
  			},
  			mc: {
  				emerald: '#4CAF50',
  				grass: '#8BC34A',
  				gold: '#FFC107',
  				redstone: '#F44336',
  				lapis: '#2196F3',
  				stone: '#7F7F7F',
  				cobblestone: '#6B6B6B',
  				wood: '#8B4513',
  				dirt: '#8B6914',
  				bedrock: '#2C2C2C',
  				glass: 'rgba(255,255,255,0.2)',
  				obsidian: '#1A1A2E',
  				diamond: '#B3E5FC',
  				iron: '#D7D7D7',
  				netherrack: '#8B0000',
  				forest: '#7CB342',
  				desert: '#F4E7B7',
  				snow: '#F0F8FF',
  				ocean: '#1976D2'
  			},
  			gradient: {
  				start: '#4CAF50',
  				middle: '#8BC34A',
  				end: '#2196F3'
  			}
  		},
  		borderRadius: {
  			none: '0px',
  			sm: '2px',
  			DEFAULT: '6px',
  			md: '6px',
  			lg: '8px',
  			xl: '12px',
  			'2xl': '16px',
  			full: '9999px',
  			pixel: '2px',
  			block: '4px'
  		},
  		fontFamily: {
  			minecraft: [
  				'Minecraft',
  				'monospace'
  			],
  			mono: [
  				'JetBrains Mono',
  				'Consolas',
  				'Monaco',
  				'Courier New',
  				'monospace'
  			]
  		},
  		fontSize: {
  			pixel: [
  				'12px',
  				{
  					lineHeight: '16px',
  					fontWeight: '500'
  				}
  			],
  			block: [
  				'14px',
  				{
  					lineHeight: '20px',
  					fontWeight: '600'
  				}
  			]
  		},
  		animation: {
  			'spin-slow': 'spin 3s linear infinite',
  			'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  			'bounce-subtle': 'bounce 2s infinite',
  			float: 'float 3s ease-in-out infinite',
  			glow: 'glow 2s ease-in-out infinite alternate',
  			shimmer: 'shimmer 2s linear infinite',
  			'exp-fill': 'exp-fill 1.5s ease-out',
  			'block-drop': 'block-drop 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  			'pixel-fade': 'pixel-fade 0.3s ease-in-out',
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		},
  		keyframes: {
  			float: {
  				'0%, 100%': {
  					transform: 'translateY(0px)'
  				},
  				'50%': {
  					transform: 'translateY(-8px)'
  				}
  			},
  			glow: {
  				'0%': {
  					boxShadow: '0 0 5px rgba(76, 175, 80, 0.5)'
  				},
  				'100%': {
  					boxShadow: '0 0 20px rgba(76, 175, 80, 0.8), 0 0 30px rgba(76, 175, 80, 0.6)'
  				}
  			},
  			shimmer: {
  				'0%': {
  					backgroundPosition: '-200% 0'
  				},
  				'100%': {
  					backgroundPosition: '200% 0'
  				}
  			},
  			'exp-fill': {
  				'0%': {
  					width: '0%'
  				},
  				'100%': {
  					width: 'var(--progress, 0%)'
  				}
  			},
  			'block-drop': {
  				'0%': {
  					transform: 'translateY(-20px) scale(0.8)',
  					opacity: '0'
  				},
  				'100%': {
  					transform: 'translateY(0) scale(1)',
  					opacity: '1'
  				}
  			},
  			'pixel-fade': {
  				'0%': {
  					opacity: '0',
  					transform: 'scale(0.95)'
  				},
  				'100%': {
  					opacity: '1',
  					transform: 'scale(1)'
  				}
  			},
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		backdropBlur: {
  			xs: '2px',
  			glass: '20px'
  		},
  		boxShadow: {
  			pixel: '2px 2px 0 rgba(0,0,0,0.3)',
  			block: '4px 4px 0 rgba(0,0,0,0.2), 8px 8px 0 rgba(0,0,0,0.1)',
  			'glow-emerald': '0 0 20px rgba(76, 175, 80, 0.3)',
  			'glow-gold': '0 0 20px rgba(255, 193, 7, 0.3)',
  			'glow-redstone': '0 0 20px rgba(244, 67, 54, 0.3)',
  			'glow-lapis': '0 0 20px rgba(33, 150, 243, 0.3)',
  			'inner-pixel': 'inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -1px 0 rgba(0,0,0,0.1)',
  			'minecraft-card': '0 4px 16px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.1)',
  			depth: '0 8px 32px rgba(0,0,0,0.12), 0 4px 16px rgba(0,0,0,0.08)'
  		},
  		backgroundImage: {
  			'grid-pattern': '`\n          linear-gradient(90deg, rgba(0,0,0,0.05) 1px, transparent 1px),\n          linear-gradient(rgba(0,0,0,0.05) 1px, transparent 1px)\n        `',
  			'noise-pattern': 'url("data:image/svg+xml,%3Csvg viewBox=\\'0 0 256 256\\' xmlns=\\'http://www.w3.org/2000/svg\\'%3E%3Cfilter id=\\'noiseFilter\\'%3E%3CfeTurbulence type=\\'fractalNoise\\' baseFrequency=\\'0.9\\' numOctaves=\\'4\\' /%3E%3C/filter%3E%3Crect width=\\'100%25\\' height=\\'100%25\\' filter=\\'url(%23noiseFilter)\\' opacity=\\'0.05\\'/%3E%3C/svg%3E")',
  			'minecraft-gradient': 'linear-gradient(135deg, #4CAF50 0%, #8BC34A 50%, #2196F3 100%)',
  			'shimmer-gradient': 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)'
  		},
  		backgroundSize: {
  			grid: '16px 16px',
  			noise: '256px 256px',
  			shimmer: '200% 100%'
  		},
  		spacing: {
  			'18': '4.5rem',
  			'88': '22rem',
  			'128': '32rem'
  		},
  		zIndex: {
  			'60': '60',
  			'70': '70',
  			'80': '80',
  			'90': '90',
  			'100': '100'
  		},
  		screens: {
  			'3xl': '1600px'
  		}
  	}
  },
  plugins: [
    // 自定义插件：Minecraft 装饰类
    function({ addUtilities, theme }) {
      const newUtilities = {
        '.pixel-perfect': {
          imageRendering: 'pixelated',
          imageRendering: '-moz-crisp-edges',
          imageRendering: 'crisp-edges',
        },
        '.text-pixel': {
          fontFamily: theme('fontFamily.minecraft'),
          textShadow: '1px 1px 0 rgba(0,0,0,0.3)',
        },
        '.bg-grid': {
          backgroundImage: theme('backgroundImage.grid-pattern'),
          backgroundSize: theme('backgroundSize.grid'),
        },
        '.bg-noise': {
          backgroundImage: theme('backgroundImage.noise-pattern'),
          backgroundSize: theme('backgroundSize.noise'),
        },
        '.glass-effect': {
          background: 'rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
        },
        '.block-shadow': {
          boxShadow: theme('boxShadow.block'),
        },
        '.pixel-shadow': {
          boxShadow: theme('boxShadow.pixel'),
        },
        '.minecraft-card': {
          background: 'linear-gradient(145deg, rgba(255,255,255,0.1) 0%, rgba(0,0,0,0.05) 100%)',
          border: '1px solid rgba(0,0,0,0.1)',
          boxShadow: theme('boxShadow.minecraft-card'),
        },
        '.exp-bar': {
          background: 'linear-gradient(90deg, #4CAF50 0%, #8BC34A 100%)',
          border: '1px solid rgba(0,0,0,0.2)',
          boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.2)',
          height: '4px',
        },
        '.shimmer': {
          backgroundImage: theme('backgroundImage.shimmer-gradient'),
          backgroundSize: theme('backgroundSize.shimmer'),
          animation: theme('animation.shimmer'),
        },
      }
      addUtilities(newUtilities)
    },
  ],
  corePlugins: {
    preflight: true,
  },
}
