import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from '@typescript-eslint/eslint-plugin'
import tsParser from '@typescript-eslint/parser'
import boundaries from 'eslint-plugin-boundaries'

/** @type {import('eslint').Linter.Config[]} */
export default [
  {
    // 忽略文件配置
    ignores: [
      'dist',
      'node_modules',
      'src-tauri',
      'archived',
      '.tsbuildinfo',
      'test-results',
      'coverage',
      'playwright-report',
    ],
  },
  {
    // 基础配置
    files: ['**/*.{js,jsx,ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.es2022,
        __APP_VERSION__: 'readonly',
        __DEV__: 'readonly',
        testUtils: 'readonly',
      },
      parser: tsParser,
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
        project: './tsconfig.json',
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      '@typescript-eslint': tseslint,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
      'boundaries': boundaries,
    },
    rules: {
      // ESLint 推荐规则
      ...js.configs.recommended.rules,
      
      // TypeScript 规则
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-non-null-assertion': 'warn',
      '@typescript-eslint/prefer-const': 'error',
      '@typescript-eslint/no-var-requires': 'error',
      '@typescript-eslint/consistent-type-imports': [
        'error',
        { prefer: 'type-imports', fixStyle: 'inline-type-imports' }
      ],
      '@typescript-eslint/no-import-type-side-effects': 'error',
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',
      '@typescript-eslint/strict-boolean-expressions': 'off',
      
      // React Hooks 规则
      ...reactHooks.configs.recommended.rules,
      
      // React Refresh 规则
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      
      // 通用规则
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'error',
      'no-alert': 'error',
      'prefer-const': 'error',
      'no-var': 'error',
      'object-shorthand': 'error',
      'prefer-arrow-callback': 'error',
      'prefer-template': 'error',
      'template-curly-spacing': ['error', 'never'],
      'quotes': ['error', 'single', { avoidEscape: true }],
      'semi': ['error', 'never'],
      'comma-dangle': ['error', 'always-multiline'],
      'eol-last': ['error', 'always'],
      'no-trailing-spaces': 'error',
      'indent': ['error', 2, { SwitchCase: 1 }],
      'max-len': ['warn', { code: 100, ignoreUrls: true }],
      
      // 架构约束规则
      'boundaries/element-types': [
        'error',
        {
          // 定义文件类型边界
          default: 'disallow',
          rules: [
            {
              from: 'components',
              allow: [
                'components',
                'hooks',
                'utils',
                'types',
                'theme',
                'assets',
              ],
            },
            {
              from: 'pages',
              allow: [
                'components',
                'hooks',
                'services',
                'stores',
                'utils',
                'types',
                'theme',
                'assets',
              ],
            },
            {
              from: 'hooks',
              allow: [
                'hooks',
                'services',
                'stores',
                'utils',
                'types',
              ],
            },
            {
              from: 'services',
              allow: [
                'services',
                'types',
                'utils',
              ],
            },
            {
              from: 'stores',
              allow: [
                'services',
                'types',
                'utils',
              ],
            },
            {
              from: 'utils',
              allow: [
                'types',
              ],
            },
            {
              from: 'types',
              allow: [],
            },
          ],
        },
      ],
    },
    settings: {
      'boundaries/elements': [
        {
          type: 'components',
          pattern: 'src/components/**/*',
        },
        {
          type: 'pages',
          pattern: 'src/pages/**/*',
        },
        {
          type: 'hooks',
          pattern: 'src/hooks/**/*',
        },
        {
          type: 'services',
          pattern: 'src/services/**/*',
        },
        {
          type: 'stores',
          pattern: 'src/stores/**/*',
        },
        {
          type: 'utils',
          pattern: 'src/utils/**/*',
        },
        {
          type: 'types',
          pattern: 'src/types/**/*',
        },
        {
          type: 'theme',
          pattern: 'src/theme/**/*',
        },
        {
          type: 'assets',
          pattern: 'src/assets/**/*',
        },
      ],
      'boundaries/ignore': [
        'src/test/**/*',
        'src/**/*.test.*',
        'src/**/*.spec.*',
        '**/*.d.ts',
      ],
    },
  },
  {
    // 测试文件特殊配置
    files: ['**/*.{test,spec}.{js,jsx,ts,tsx}', 'src/test/**/*'],
    languageOptions: {
      globals: {
        ...globals.jest,
        vi: 'readonly',
        expect: 'readonly',
        describe: 'readonly',
        it: 'readonly',
        test: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        beforeAll: 'readonly',
        afterAll: 'readonly',
      },
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      'no-console': 'off',
    },
  },
  {
    // 配置文件特殊规则
    files: ['*.config.{js,ts}', '*.setup.{js,ts}'],
    rules: {
      'no-console': 'off',
      '@typescript-eslint/no-var-requires': 'off',
    },
  },
]