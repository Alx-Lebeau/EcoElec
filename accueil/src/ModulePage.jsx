import { NBSP, OPTIONS, isDraft, minutes } from "./format.js";
import { Action, Icon, NEW_TAB, Tag } from "./ui.jsx";

function Durations({ module, labels }) {
  const rows = [
    ["Base", module.duree],
    ...OPTIONS.filter((o) => module.supplements[o] !== 0).map((o) => [
      `+${NBSP}${labels[o]}`,
      module.supplements[o],
    ]),
  ];
  return (
    <dl className="facts">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{minutes(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function Uses({ module, catalogue }) {
  if (!module.utilisations.length)
    return <p className="muted">Aucun parcours ne l'utilise pour l'instant.</p>;
  return (
    <ul className="plain-list">
      {module.utilisations.map(({ parcours, seance }) => {
        const track = catalogue.parcours.find((t) => t.nom === parcours);
        const session = track.seances.find((s) => s.numero === seance);
        return (
          <li key={`${parcours}-${seance}`}>
            <a href={`#/parcours/${parcours}`}>
              <span className="track-badge track-badge-small">{parcours}</span>
              Séance {seance}
              {NBSP}: {session.titre}
            </a>
          </li>
        );
      })}
    </ul>
  );
}

export default function ModulePage({ module, catalogue, modules }) {
  const labels = catalogue.options;
  const number = catalogue.modules.indexOf(module) + 1;
  return (
    <main className="container page">
      <a className="back" href="#/modules">
        <Icon name="back" size={16} /> Tous les modules
      </a>
      <header className="page-head">
        <p className="eyebrow">Module {String(number).padStart(2, "0")}</p>
        <h1>{module.titre}</h1>
        {isDraft(module) && (
          <div className="tags">
            <Tag kind="ebauche">en rédaction</Tag>
          </div>
        )}
      </header>

      <div className="module-layout">
        <div className="module-main">
          <section className="card">
            <h2>Objectifs</h2>
            {module.objectifs.length ? (
              <ul className="objectives">
                {module.objectifs.map((o) => (
                  <li key={o}>{o}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">À rédiger.</p>
            )}
          </section>

          <section className="card">
            <h2>Ressources</h2>
            <div className="resources">
              <Action href={module.chapitre} icon="book" variant="primary">
                Chapitre du poly
              </Action>
              <Action href={module.slides.base} icon="slides" newTab>
                Slides, base
              </Action>
              <Action
                href={module.slides.integral}
                icon="slides"
                newTab
                title={`Base, ${labels.approfondissement} et ${labels.formel}`}
              >
                Slides, intégral
              </Action>
              {module.outil && (
                <Action href={module.outil} icon="tool">
                  Outil interactif
                </Action>
              )}
            </div>
            {module.tp.length > 0 && (
              <p className="muted small">
                Travaux pratiques (TP){NBSP}: {module.tp.join(", ")} (notebooks du dépôt).
              </p>
            )}
            <p className="small">
              <a className="subtle-link" href={module.slides.auteur} {...NEW_TAB}>
                <Icon name="eye" size={14} /> Vue auteur{NBSP}: tout le contenu, marques visibles
              </a>
            </p>
          </section>
        </div>

        <aside className="module-side">
          <section className="card">
            <h2>Durée</h2>
            <Durations module={module} labels={labels} />
          </section>
          <section className="card">
            <h2>Prérequis</h2>
            {module.prerequis.length ? (
              <ul className="plain-list">
                {module.prerequis.map((id) => (
                  <li key={id}>
                    <a href={`#/modules/${id}`}>{modules[id]?.titre ?? id}</a>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">Aucun.</p>
            )}
          </section>
          <section className="card">
            <h2>Dans les parcours</h2>
            <Uses module={module} catalogue={catalogue} />
          </section>
        </aside>
      </div>
    </main>
  );
}
