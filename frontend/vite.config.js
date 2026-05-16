// frontend/vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  server: {
    host: "0.0.0.0",   // Docker コンテナ内からアクセス可能にする
    port: 5173,

    // 開発時: /api/* を backend に透過プロキシ
    // → VITE_API_BASE を /api にすれば本番と同じパスで動く
    proxy: {
      "/api": {
        target: "http://backend:8000",  // Docker内部ネットワーク名
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
