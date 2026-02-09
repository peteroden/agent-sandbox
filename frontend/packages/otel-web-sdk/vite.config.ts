import { defineConfig } from 'vite'
import { resolve } from 'path'
import dts from 'vite-plugin-dts'
import pkg from './package.json'

export default defineConfig({
  define: {
    __PKG_NAME__: JSON.stringify(pkg.name),
    __PKG_VERSION__: JSON.stringify(pkg.version),
  },
  plugins: [
    dts({ 
      include: ['src/**/*.ts', 'src/**/*.tsx'],
      outDir: 'dist',
      rollupTypes: false,
      entryRoot: 'src',
    }),
  ],
  build: {
    lib: {
      entry: {
        index: resolve(__dirname, 'src/index.ts'),
        'react/index': resolve(__dirname, 'src/react/index.ts'),
      },
      formats: ['es'],
      fileName: (_, entryName) => `${entryName}.mjs`,
    },
    rollupOptions: {
      external: [
        '@opentelemetry/api',
        '@opentelemetry/api-logs',
        'preact',
        'preact/hooks',
        'preact/compat',
      ],
      output: {
        preserveModules: false,
      },
    },
    outDir: 'dist',
    sourcemap: true,
    minify: false,
  },
})
