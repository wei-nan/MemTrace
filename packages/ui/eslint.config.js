import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // Legacy graph/plugin payloads are structurally dynamic. New API modules
      // should still prefer unknown and explicit interfaces.
      '@typescript-eslint/no-explicit-any': 'off',
      // Existing pages intentionally start async loading from effects. These
      // React Compiler advisory rules reject that established pattern.
      'react-hooks/set-state-in-effect': 'off',
      'react-hooks/preserve-manual-memoization': 'off',
      // Dependency cleanup is being handled page-by-page; forcing automated
      // additions here can change request and polling behavior.
      'react-hooks/exhaustive-deps': 'off',
    },
  },
])
