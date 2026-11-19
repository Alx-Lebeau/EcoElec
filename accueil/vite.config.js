// Accueil du site publié, construit à la racine du rendu (_rendu/index.html et
// _rendu/accueil/) à côté des rendus Quarto (poly/, slides/, autonome/, outils/),
// qu'il ne faut pas effacer : emptyOutDir à false.
// Données : decks/catalogue.json, écrit par `uv run ecoelec generer`.
// `npm run preview` sert tout _rendu/ (liens vers le poly et les slides compris).
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  base: "./",
  publicDir: false,
  build: {
    outDir: "../_rendu",
    emptyOutDir: false,
    assetsDir: "accueil",
  },
  server: { fs: { allow: [".."] } },
});
