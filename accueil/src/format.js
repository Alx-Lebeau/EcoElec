// Libellés et mises en forme. Typographie française : espace insécable fine avant
// « : » et entre nombre et unité (NBSP), comme typographie.lua dans les rendus Quarto.
export const NBSP = " ";

// Ordre des options, comme OPTIONS dans outils/__init__.py
export const OPTIONS = ["approfondissement", "formel"];

/** Libellé d'un choix d'options : « base », « avec formalisme »… */
export function optionsLabel(options, labels) {
  const chosen = OPTIONS.filter((o) => options.includes(o)).map((o) => labels[o]);
  return chosen.length ? `avec ${chosen.join(" et ")}` : "base";
}

/** 45 → « 45 min », 90 → « 1 h 30 », 360 → « 6 h », null → « à estimer ». */
export function minutes(value) {
  if (value === null || value === undefined) return "à estimer";
  if (value < 60) return `${value}${NBSP}min`;
  const h = Math.floor(value / 60);
  const m = value % 60;
  return m ? `${h}${NBSP}h${NBSP}${String(m).padStart(2, "0")}` : `${h}${NBSP}h`;
}

export function plural(n, word) {
  return `${n}${NBSP}${word}${n > 1 ? "s" : ""}`;
}

/** Module encore en ébauche : ni objectifs ni durée. */
export function isDraft(module) {
  return module.objectifs.length === 0 && module.duree === null;
}
