import { defineConfig } from "vite";

// GitHub Pages sert le site sous /<repo>/.
// Le workflow définit BASE_PATH="</repo>/" pour le build.
export default defineConfig({
  base: process.env.BASE_PATH ?? "/",
});

