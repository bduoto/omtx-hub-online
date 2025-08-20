import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 5173,
    // Removed proxy - frontend will call production API directly
  },
  plugins: [
    react(),
    mode === 'development' &&
    componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  optimizeDeps: {
    include: [
      'molstar/lib/mol-plugin/context',
      'molstar/lib/mol-plugin/spec',
      'molstar/lib/mol-canvas3d/canvas3d',
      'molstar/lib/mol-plugin/commands'
    ],
    exclude: ['molstar']
  },
  build: {
    rollupOptions: {
      external: (id) => {
        // Keep molstar as external for dynamic imports
        return id.includes('molstar') && !id.includes('mol-plugin-ui');
      }
    }
  }
}));
