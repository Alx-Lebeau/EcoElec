"""Lecture et vérification des parcours (parcours/<nom>.yml).

Format :

    titre: Comprendre le prix de l'électricité
    formalisme: intuitif                 # par défaut pour tout le parcours
    seances:
      - titre: Du merit order au prix de long terme
        duree: 90                        # minutes
        introduction: parcours/textes/accueil.qmd   # facultatif
        conclusion: parcours/textes/bilan.qmd       # facultatif
        modules:
          - court-terme: essentiel
          - long-terme: {profondeur: complet, formalisme: formel}   # exception
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from outils import DEPTHS, FORMALISMS
from outils.catalog import Module
from outils.report import Report

TRACK_KEYS = {"titre", "formalisme", "seances"}
SESSION_KEYS = {"titre", "duree", "modules", "introduction", "conclusion"}


@dataclass
class Entry:
    """Un module dans une séance, avec sa version et les prérequis qui ne le précèdent pas."""

    module: Module
    depth: str
    formalism: str
    missing: list[str] = field(default_factory=list)

    @property
    def duration(self) -> int | None:
        return self.module.duration(self.depth, self.formalism)


@dataclass
class Session:
    number: int
    title: str
    duration: int
    entries: list[Entry]
    introduction: str | None = None
    conclusion: str | None = None

    @property
    def declared(self) -> int | None:
        """Somme des durées déclarées des modules, ou None si l'une n'est pas estimée."""
        values = [e.duration for e in self.entries]
        return None if any(v is None for v in values) else sum(values)


@dataclass
class Track:
    name: str
    path: Path
    title: str
    formalism: str
    sessions: list[Session]

    def entries(self) -> list[Entry]:
        return [e for s in self.sessions for e in s.entries]


def load_tracks(root: Path, modules: dict[str, Module], report: Report) -> list[Track]:
    tracks = []
    for path in sorted((root / "parcours").glob("*.yml"), key=_natural_key):
        track = _load_track(path, root, modules, report)
        if track:
            tracks.append(track)
    return tracks


def _natural_key(path: Path) -> list:
    """Tri naturel : 3h, 6h, 12h plutôt que 12h, 3h, 6h."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", path.stem)]


def _load_track(path: Path, root: Path, modules: dict[str, Module], report: Report) -> Track | None:
    where = str(path.relative_to(root))
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        report.error(where, f"fichier illisible ({exc})")
        return None

    unknown = set(data) - TRACK_KEYS
    if unknown:
        report.warning(where, f"clés inconnues : {', '.join(sorted(unknown))}")
    title = data.get("titre")
    if not isinstance(title, str) or not title.strip():
        report.error(where, "titre manquant")
        return None
    formalism = data.get("formalisme")
    if formalism not in FORMALISMS:
        report.error(
            where, f"formalisme du parcours : {' ou '.join(FORMALISMS)} attendu, pas {formalism!r}"
        )
        return None
    raw_sessions = data.get("seances")
    if not isinstance(raw_sessions, list) or not raw_sessions:
        report.error(where, "aucune séance")
        return None

    sessions = []
    for number, raw in enumerate(raw_sessions, start=1):
        session = _read_session(
            raw, number, formalism, f"{where}, séance {number}", root, modules, report
        )
        if session:
            sessions.append(session)
    track = Track(path.stem, path, title.strip(), formalism, sessions)
    _check_track(track, where, report)
    return track


def _read_session(raw, number, formalism, where, root, modules, report) -> Session | None:
    if not isinstance(raw, dict):
        report.error(where, "séance mal formée")
        return None
    unknown = set(raw) - SESSION_KEYS
    if unknown:
        report.warning(where, f"clés inconnues : {', '.join(sorted(unknown))}")
    title = raw.get("titre")
    duration = raw.get("duree")
    if not isinstance(title, str) or not title.strip():
        report.error(where, "titre manquant")
        return None
    if not isinstance(duration, int) or duration <= 0:
        report.error(where, "durée (en minutes) manquante ou invalide")
        return None
    for key in ("introduction", "conclusion"):
        if raw.get(key) and not (root / raw[key]).exists():
            report.error(where, f"{key} introuvable : {raw[key]}")

    entries = []
    for item in raw.get("modules") or []:
        entry = _read_entry(item, formalism, where, modules, report)
        if entry:
            entries.append(entry)
    if not entries:
        report.error(where, "aucun module")
        return None
    return Session(
        number, title.strip(), duration, entries, raw.get("introduction"), raw.get("conclusion")
    )


def _read_entry(item, formalism, where, modules, report) -> Entry | None:
    if not isinstance(item, dict) or len(item) != 1:
        report.error(where, f"entrée de module mal formée : {item!r}")
        return None
    ((module_id, spec),) = item.items()
    if module_id not in modules:
        report.error(where, f"module inconnu : {module_id}")
        return None
    module = modules[module_id]
    if module.is_example:
        report.error(where, f"{module_id} est un module d'exemple, hors parcours")
        return None
    if isinstance(spec, str):
        depth, entry_formalism = spec, formalism
    elif isinstance(spec, dict):
        depth, entry_formalism = spec.get("profondeur"), spec.get("formalisme", formalism)
    else:
        report.error(where, f"{module_id} : version mal formée ({spec!r})")
        return None
    if depth not in DEPTHS:
        report.error(
            where, f"{module_id} : profondeur {' ou '.join(DEPTHS)} attendue, pas {depth!r}"
        )
        return None
    if entry_formalism not in FORMALISMS:
        report.error(
            where,
            f"{module_id} : formalisme {' ou '.join(FORMALISMS)} attendu, pas {entry_formalism!r}",
        )
        return None
    return Entry(module, depth, entry_formalism)


def _check_track(track: Track, where: str, report: Report) -> None:
    seen: set[str] = set()
    for session in track.sessions:
        swhere = f"{where}, séance {session.number}"
        # Durées
        declared = session.declared
        if declared is None:
            pending = sorted({e.module.id for e in session.entries if e.duration is None})
            report.warning(swhere, f"durée non vérifiable, durées à estimer : {', '.join(pending)}")
        elif declared > session.duration:
            report.error(
                swhere, f"durée dépassée : {declared} min de modules pour {session.duration} min"
            )
        # Prérequis et doublons
        for entry in session.entries:
            mid = entry.module.id
            if mid in seen:
                report.warning(swhere, f"{mid} apparaît plusieurs fois dans le parcours")
            entry.missing = [p for p in entry.module.prerequisites if p not in seen]
            if entry.missing:
                missing = ", ".join(entry.missing)
                if entry.module.has_recall:
                    report.info(
                        swhere, f"{mid} : rappels inclus (prérequis absents en amont : {missing})"
                    )
                else:
                    report.warning(
                        swhere,
                        f"{mid} : prérequis absents en amont ({missing}) et aucune slide de rappel",
                    )
            seen.add(mid)
