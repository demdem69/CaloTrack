import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// GitHub Pages sert le site sous /<repo>/.
// Le workflow définit BASE_PATH="</repo>/" pour le build.
export default defineConfig({
  plugins: [react()],
  base: process.env.BASE_PATH ?? "/",
});

