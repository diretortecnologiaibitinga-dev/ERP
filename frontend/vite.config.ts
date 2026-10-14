import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Modo "pagina": um único JS (IIFE) com React externo (carregado do CDN), para
// montar uma página estática de demonstração (scripts/montar-pagina.mjs).
export default defineConfig(({ mode }) =>
  mode === "pagina"
    ? {
        esbuild: { jsx: "transform", jsxFactory: "React.createElement", jsxFragment: "React.Fragment",
                   jsxInject: `import React from "react"` },
        build: {
          outDir: "dist-pagina",
          cssCodeSplit: false,
          rollupOptions: {
            input: "src/main.tsx",
            external: ["react", "react-dom", "react-dom/client"],
            output: {
              format: "iife",
              entryFileNames: "app.js",
              assetFileNames: "app.[ext]",
              globals: { react: "React", "react-dom": "ReactDOM", "react-dom/client": "ReactDOM" },
            },
          },
        },
      }
    : { plugins: [react()] },
);
