import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    allowedHosts:true, 
    
    // proxy: {
    //   '/api': {
    //     target: 'https://aka-settlement-missions-secret.trycloudflare.com',
    //     changeOrigin: true,
    //     secure: false,
        
    //   },
    //   '/ws': {
    //     target: 'https://aka-settlement-missions-secret.trycloudflare.com',
    //     ws: true,
    //   },
    // },
  },
})
