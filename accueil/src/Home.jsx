import { NBSP, isDraft, minutes, optionsLabel, plural } from "./format.js";
import { Action, Icon, OptionTags, Tag } from "./ui.jsx";

function Hero({ catalogue }) {
  const { poly } = catalogue;
  return (
    <section className="hero">
      <div className="container hero-inner">
        <p className="eyebrow">Cours modulaire</p>
        <h1>{catalogue.titre}</h1>
        <p className="hero-subtitle">{catalogue.sous_titre}</p>
        <p className="hero-text">
          Chaque parcours réunit les slides de ses séances, les chapitres du poly à lire et les
          outils de simulation. Le poly couvre l'ensemble des modules.
        </p>
        <div className="hero-actions">
          <Action href="#/parcours" icon="arrow" variant="primary">
            Choisir un parcours
          </Action>
          <Action href={poly.html} icon="book" variant="ghost">
            Lire le poly
          </Action>
          <Action href={poly.pdf} icon="download" variant="ghost">
            Poly en PDF
          </Action>
        </div>
      </div>
    </section>
  );
}

function TrackCard({ track, labels }) {
  const count = new Set(track.seances.flatMap((s) => s.modules.map((m) => m.id))).size;
  return (
    <a className="card card-link track-card" href={`#/parcours/${track.nom}`}>
      <span className="track-badge">{track.nom}</span>
      <h3>{track.titre}</h3>
      <p className="muted">
        {plural(track.seances.length, "séance")} · {minutes(track.duree)} ·{" "}
        {plural(count, "module")}
      </p>
      <div className="tags" title={`Modules ${optionsLabel(track.options, labels)}`}>
        <OptionTags options={track.options} labels={labels} />
      </div>
      <span className="card-more">
        Voir les séances <Icon name="arrow" size={16} />
      </span>
    </a>
  );
}

function ModuleCard({ module, number }) {
  return (
    <a className="card card-link module-card" href={`#/modules/${module.id}`}>
      <span className="module-number">{String(number).padStart(2, "0")}</span>
      <div className="module-card-body">
        <h3>{module.titre}</h3>
        <div className="tags">
          {isDraft(module) ? (
            <Tag kind="ebauche">en rédaction</Tag>
          ) : (
            <Tag>
              <Icon name="clock" size={13} />
              {minutes(module.duree)}
            </Tag>
          )}
          {module.outil && <Tag kind="outil">outil</Tag>}
          {module.tp.length > 0 && (
            <Tag kind="tp" title="Travaux pratiques (notebooks)">
              TP
            </Tag>
          )}
        </div>
      </div>
    </a>
  );
}

function ToolCard({ module }) {
  return (
    <a className="card card-link tool-card" href={module.outil}>
      <span className="tool-icon">
        <Icon name="tool" size={22} />
      </span>
      <div>
        <h3>{module.titre}</h3>
        <p className="muted">Simulation interactive, dans le navigateur</p>
      </div>
    </a>
  );
}

export default function Home({ catalogue }) {
  const tools = catalogue.modules.filter((m) => m.outil);
  return (
    <main>
      <Hero catalogue={catalogue} />

      <section className="container section" id="parcours">
        <div className="section-head">
          <h2>Parcours</h2>
          <p className="muted">
            Un parcours par format ou par session. Chacun prend la base des modules et, selon le
            public, les approfondissements ou le formalisme mathématique.
          </p>
        </div>
        <div className="grid grid-tracks">
          {catalogue.parcours.map((t) => (
            <TrackCard key={t.nom} track={t} labels={catalogue.options} />
          ))}
        </div>
      </section>

      <section className="container section" id="modules">
        <div className="section-head">
          <h2>Modules</h2>
          <p className="muted">
            Dans l'ordre du poly, un chapitre par module. Chaque fiche donne les objectifs, les
            prérequis, les slides et les parcours qui l'utilisent.
          </p>
        </div>
        <div className="grid grid-modules">
          {catalogue.modules.map((m, i) => (
            <ModuleCard key={m.id} module={m} number={i + 1} />
          ))}
        </div>
      </section>

      {tools.length > 0 && (
        <section className="container section" id="outils">
          <div className="section-head">
            <h2>Outils interactifs</h2>
            <p className="muted">
              Les modèles du cours, à manipuler{NBSP}: hypothèses modifiables, résultats
              recalculés immédiatement.
            </p>
          </div>
          <div className="grid grid-tools">
            {tools.map((m) => (
              <ToolCard key={m.id} module={m} />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
