// Accueil du site : une page, trois vues adressées par le fragment de l'URL
// (GitHub Pages ne sert que des fichiers, d'où #/… plutôt que des chemins) :
//   #/                    accueil (#/parcours, #/modules, #/outils : sections de l'accueil)
//   #/parcours/<nom>      séances d'un parcours
//   #/modules/<id>        fiche d'un module
import { useEffect, useState } from "react";
import logo from "../../commun/logo.svg";
import catalogue from "../../decks/catalogue.json";
import Home from "./Home.jsx";
import ModulePage from "./ModulePage.jsx";
import TrackPage from "./TrackPage.jsx";
import { Icon } from "./ui.jsx";

function readRoute() {
  const [section = "", id = ""] = window.location.hash.replace(/^#\/?/, "").split("/");
  return { section: decodeURIComponent(section), id: decodeURIComponent(id) };
}

function useRoute() {
  const [route, setRoute] = useState(readRoute);
  useEffect(() => {
    const update = () => setRoute(readRoute());
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  return route;
}

function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || null);
  const dark =
    theme === "dark" ||
    (theme === null && window.matchMedia("(prefers-color-scheme: dark)").matches);
  const toggle = () => {
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      // Clé et valeurs de Quarto : le choix vaut aussi pour le poly et les outils
      localStorage.setItem("quarto-color-scheme", next === "dark" ? "alternate" : "default");
    } catch {
      // stockage indisponible (navigation privée) : thème non mémorisé
    }
    setTheme(next);
  };
  return [dark, toggle];
}

function Header({ section }) {
  const [dark, toggleTheme] = useTheme();
  const links = [
    ["parcours", "Parcours", "#/parcours"],
    ["modules", "Modules", "#/modules"],
    ["outils", "Outils", "#/outils"],
  ];
  return (
    <header className="site-header">
      <div className="container header-inner">
        <a className="brand" href="#/">
          <img className="brand-mark" src={logo} width="28" height="28" alt="" />
          <span>{catalogue.titre}</span>
        </a>
        <nav className="nav" aria-label="Navigation principale">
          {links.map(([key, label, href]) => (
            <a key={key} href={href} aria-current={section === key ? "page" : undefined}>
              {label}
            </a>
          ))}
          <a href={catalogue.poly.html}>Poly</a>
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={dark ? "Passer au thème clair" : "Passer au thème sombre"}
            title={dark ? "Thème clair" : "Thème sombre"}
          >
            <Icon name={dark ? "sun" : "moon"} />
          </button>
        </nav>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="site-footer">
      <div className="container footer-inner">
        <span>
          {catalogue.titre} · {catalogue.auteur}
        </span>
        <span>Contenu sous licence CC BY-SA 4.0, code sous licence MIT.</span>
      </div>
    </footer>
  );
}

function NotFound({ what }) {
  return (
    <main className="container page">
      <h1>Page introuvable</h1>
      <p className="muted">Aucun {what} ne porte ce nom.</p>
      <p>
        <a href="#/">Retour à l'accueil</a>
      </p>
    </main>
  );
}

export default function App() {
  const { section, id } = useRoute();
  const modules = Object.fromEntries(catalogue.modules.map((m) => [m.id, m]));

  // Changement de vue : haut de page, ou section de l'accueil demandée
  useEffect(() => {
    if (id) window.scrollTo(0, 0);
    else if (section) document.getElementById(section)?.scrollIntoView();
    else window.scrollTo(0, 0);
  }, [section, id]);

  useEffect(() => {
    const track = section === "parcours" && catalogue.parcours.find((t) => t.nom === id);
    const module = section === "modules" && modules[id];
    const page = track?.titre || module?.titre;
    document.title = page && page !== catalogue.titre ? `${page} · ${catalogue.titre}` : catalogue.titre;
  });

  let content;
  if (section === "parcours" && id) {
    const track = catalogue.parcours.find((t) => t.nom === id);
    content = track ? (
      <TrackPage track={track} catalogue={catalogue} modules={modules} />
    ) : (
      <NotFound what="parcours" />
    );
  } else if (section === "modules" && id) {
    content = modules[id] ? (
      <ModulePage module={modules[id]} catalogue={catalogue} modules={modules} />
    ) : (
      <NotFound what="module" />
    );
  } else {
    content = <Home catalogue={catalogue} />;
  }

  return (
    <>
      <Header section={id ? section : ""} />
      {content}
      <Footer />
    </>
  );
}
