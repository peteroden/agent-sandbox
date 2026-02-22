import { defineConfig } from 'vitest/config'
import pkg from './package.json'

export default defineConfig({
  define: {
    __PKG_NAME__: JSON.stringify(pkg.name),
    __PKG_VERSION__: JSON.stringify(pkg.version),
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    include: ['test/**/*.test.ts', 'test/**/*.test.tsx'],
    testTimeout: 15000,
    hookTimeout: 15000,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts', 'src/**/*.tsx'],
    },
  },
  resolve: {
    alias: {
      'react': 'preact/compat',
      'react-dom': 'preact/compat',
    },
  },
})
