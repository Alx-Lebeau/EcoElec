// Éléments d'interface communs aux pages.

const ICONS = {
  slides: "M3 4h18v12H3zM8 20h8M12 16v4",
  book: "M4 4.5A2.5 2.5 0 0 1 6.5 2H20v17H6.5A2.5 2.5 0 0 0 4 21.5zM4 21.5A2.5 2.5 0 0 1 6.5 19H20v3H6.5",
  download: "M12 3v12M7 10l5 5 5-5M4 21h16",
  tool: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  clock: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2",
  arrow: "M5 12h14M13 6l6 6-6 6",
  back: "M19 12H5M11 6l-6 6 6 6",
  link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
  sun: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  moon: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z",
  bolt: "M13 2 4 14h7l-1 8 9-12h-7z",
};

export function Icon({ name, size = 18 }) {
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={ICONS[name]} />
    </svg>
  );
}

/** Attributs d'un lien vers des slides : nouvel onglet, l'accueil reste ouvert. */
export const NEW_TAB = { target: "_blank", rel: "noopener" };

/** Lien-bouton vers un rendu Quarto (chemin relatif à la racine du site).
 *  `download` : nom du fichier enregistré, au lieu de l'ouvrir (même origine seulement). */
export function Action({
  href,
  icon,
  children,
  variant = "secondary",
  title,
  newTab = false,
  download,
}) {
  return (
    <a
      className={`action action-${variant}`}
      href={href}
      title={title}
      download={download}
      {...(newTab ? NEW_TAB : {})}
    >
      {icon && <Icon name={icon} />}
      <span>{children}</span>
    </a>
  );
}

export function Tag({ kind = "neutre", children, title }) {
  return (
    <span className={`tag tag-${kind}`} title={title}>
      {children}
    </span>
  );
}

/** Étiquettes des options d'un module ou d'un parcours. */
export function OptionTags({ options, labels }) {
  if (!options.length) return <Tag>base</Tag>;
  return options.map((o) => (
    <Tag key={o} kind={o}>
      {labels[o]}
    </Tag>
  ));
}
