import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  server: {
    // The FastAPI backend (storelab/main.py) runs separately in dev — `uvicorn storelab.main:app --port 8080`.
    // In production this doesn't matter: the backend serves the built frontend itself, same origin.
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
  // The backend only serves static files under /static (storelab/main.py mounts
  // RevalidatedStaticFiles at /static). So built asset URLs must carry that prefix — but the
  // build output itself stays in the default frontend/dist: the repo's web/ directory is
  // retired, not a build target. The Dockerfile copies this stage's dist/ into the image's
  // own web/ at build time; nothing here writes outside frontend/.
  base: command === 'build' ? '/static/' : '/',
}))
