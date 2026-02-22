import { defineConfig } from 'vite'
import { resolve } from 'node:path'

/**
 * Separate Vite config for building the bootstrap IIFE script.
 *
 * The bootstrap script must be a pure IIFE that runs immediately
 * before any other JavaScript. It cannot be an ES module.
 */
export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, 'src/bootstrap.ts'),
      formats: ['iife'],
      name: 'OTelBootstrap',
      fileName: () => 'bootstrap.iife.js',
    },
    outDir: 'dist',
    emptyOutDir: false, // Don't clear dist (other builds go there too)
    sourcemap: false, // Keep IIFE small and simple
    minify: true,
    rollupOptions: {
      output: {
        // Ensure it runs immediately (IIFE pattern)
        extend: true,
      },
    },
  },
})
