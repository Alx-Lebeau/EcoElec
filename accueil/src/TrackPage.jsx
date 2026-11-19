import { useState } from "react";
import { NBSP, minutes, optionsLabel, plural } from "./format.js";
import { Action, Icon, OptionTags, Tag } from "./ui.jsx";

/** Adresse courte du parcours (_rendu/parcours/<nom>/, écrite par `ecoelec site`). */
function ShortLink({ name }) {
  const url = new URL(`parcours/${name}/`, window.location.href.split("#")[0]).href;
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // presse-papiers refusé : l'adresse reste affichée
    }
  };
  return (
    <div className="short-link">
      <span className="muted">Adresse à donner au public</span>
      <code>{url}</code>
      <button type="button" className="action action-secondary" onClick={copy}>
        <Icon name="link" />
        <span>{copied ? "Copiée" : "Copier"}</span>
      </button>
    </div>
  );
}

function Timing({ session }) {
  const planned = session.duree;
  const declared = session.duree_modules;
  const ratio = declared === null ? null : Math.min(declared / planned, 1);
  return (
    <div className="timing">
      <div className="timing-text">
        <Icon name="clock" size={15} />
        <span>
          {minutes(planned)} prévues · modules{NBSP}: {minutes(declared)}
        </span>
      </div>
      <div className="timing-bar" aria-hidden="true">
        {ratio !== null && <span style={{ width: `${ratio * 100}%` }} />}
      </div>
    </div>
  );
}

function SessionModule({ entry, modules, labels }) {
  const module = modules[entry.id];
  const recalls = entry.rappels.map((id) => modules[id]?.titre ?? id);
  return (
    <li className="session-module">
      <div className="session-module-main">
        <a className="session-module-title" href={`#/modules/${module.id}`}>
          {module.titre}
        </a>
        <div className="tags">
          <Tag kind={entry.options.length ? "option" : "neutre"}>
            {optionsLabel(entry.options, labels)}
          </Tag>
          <Tag>{minutes(entry.duree)}</Tag>
        </div>
        {recalls.length > 0 && (
          <p className="recall">
            Rappels inclus, le prérequis ne précédant pas le module{NBSP}: {recalls.join(", ")}
          </p>
        )}
      </div>
      <div className="session-module-links">
        <a href={module.chapitre}>
          <Icon name="book" size={15} /> Chapitre
        </a>
        {module.outil && (
          <a href={module.outil}>
            <Icon name="tool" size={15} /> Outil
          </a>
        )}
      </div>
    </li>
  );
}

function Session({ track, session, modules, labels }) {
  const file = `economie-electricite-${track.nom}-seance-${String(session.numero).padStart(2, "0")}`;
  return (
    <li className="card session">
      <div className="session-head">
        <span className="session-number">{session.numero}</span>
        <div className="session-title">
          <h2>{session.titre}</h2>
          <Timing session={session} />
        </div>
      </div>
      <div className="session-actions">
        <Action href={session.deck} icon="slides" variant="primary" newTab>
          Slides
        </Action>
        <Action
          href={session.autonome}
          icon="download"
          title="Télécharger le deck en un seul fichier HTML, projetable sans connexion"
          download={`${file}.html`}
        >
          HTML
        </Action>
        <Action
          href={session.pdf}
          icon="download"
          title="Télécharger le deck en PDF"
          download={`${file}.pdf`}
        >
          PDF
        </Action>
      </div>
      <h3 className="session-subtitle">Modules et chapitres du poly à lire</h3>
      <ul className="session-modules">
        {session.modules.map((e) => (
          <SessionModule key={e.id} entry={e} modules={modules} labels={labels} />
        ))}
      </ul>
    </li>
  );
}

export default function TrackPage({ track, catalogue, modules }) {
  const labels = catalogue.options;
  return (
    <main className="container page">
      <a className="back" href="#/parcours">
        <Icon name="back" size={16} /> Tous les parcours
      </a>
      <header className="page-head">
        <span className="track-badge">{track.nom}</span>
        <h1>{track.titre}</h1>
        <p className="muted">
          {plural(track.seances.length, "séance")} · {minutes(track.duree)} · modules{" "}
          {optionsLabel(track.options, labels)}
        </p>
        <div className="tags">
          <OptionTags options={track.options} labels={labels} />
        </div>
        <ShortLink name={track.nom} />
      </header>
      <ol className="sessions">
        {track.seances.map((s) => (
          <Session key={s.numero} track={track} session={s} modules={modules} labels={labels} />
        ))}
      </ol>
    </main>
  );
}
