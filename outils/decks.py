"""Génération des decks dans decks/ (dossier généré, non versionné).

    decks/modules/<module>/base.qmd                        la base seule, sans option
    decks/modules/<module>/integral.qmd                    la base et toutes les options
    decks/modules/<module>/auteur.qmd                      vue auteur : tout, marques visibles
    decks/parcours/<parcours>/seance-NN.qmd                un deck par séance
    decks/parcours/<parcours>/index.qmd                    séances, durées, chapitres du poly à lire
    decks/index.qmd                                        page d'accueil des slides

Chaque deck inclut le contenu des modules (`{{< include >}}`) précédé d'un
marqueur d'options lu par commun/filtres/marques.lua.

Empreinte : `freeze: auto` ne réexécute un document que si son propre texte
change, pas celui des fichiers qu'il inclut. Chaque deck porte donc dans ses
métadonnées une empreinte de ses sources (fichiers inclus, pyelec/, data/) :
toute modification de l'une d'elles modifie le deck et déclenche la réexécution.
"""

import hashlib
import shutil
from pathlib import Path

import yaml

from outils import OPTIONS, options_label
from outils.catalog import Module
from outils.tracks import Entry, Session, Track

OUTPUT = "decks"
STAMP = ".genere-par-ecoelec"
# Decks isolés de chaque module : les deux extrêmes. Les combinaisons intermédiaires
# sont rendues par les decks des parcours qui les utilisent.
MODULE_DECKS = {"base": (), "integral": OPTIONS}


# Sources communes à tous les decks qui exécutent du code
SHARED_SOURCES = ("commun/_macros.qmd", "pyelec", "data")


def _fingerprint(root: Path, sources: list[str]) -> str:
    """Empreinte du contenu des fichiers (ou dossiers) donnés, relatifs à la racine."""
    digest = hashlib.sha256()
    for source in [*SHARED_SOURCES, *sources]:
        path = root / source
        files = sorted(f for f in path.rglob("*") if f.is_file()) if path.is_dir() else [path]
        for f in files:
            if f.exists() and "__pycache__" not in f.parts:
                digest.update(str(f.relative_to(root)).encode())
                digest.update(f.read_bytes())
    return digest.hexdigest()[:16]


def generate(root: Path, modules: dict[str, Module], tracks: list[Track]) -> list[Path]:
    out = root / OUTPUT
    _reset(out)
    written = []
    for module in modules.values():
        written += _module_decks(root, out, module)
    for track in tracks:
        written += _track_decks(root, out, track)
    written.append(_write(out / "index.qmd", _site_index(modules, tracks)))
    return written


def _reset(out: Path) -> None:
    if out.exists():
        if not (out / STAMP).exists():
            raise RuntimeError(
                f"{out} existe mais n'a pas été généré par ecoelec : suppression refusée"
            )
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / STAMP).write_text(
        "Dossier généré par `ecoelec generer` : ne pas éditer.\n", encoding="utf-8"
    )


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _front_matter(**fields) -> str:
    dumped = yaml.safe_dump(fields, allow_unicode=True, sort_keys=False, width=1000)
    return f"---\n{dumped}---\n"


def _marker(module: Module, options, missing: list[str]) -> str:
    return (
        f'::: {{.ecoelec-module module="{module.id}" options="{" ".join(options)}" '
        f'manquants="{" ".join(missing)}"}}\n:::\n'
    )


def _module_body(module: Module, options, missing: list[str], section_title: bool) -> str:
    parts = [_marker(module, options, missing)]
    if section_title:
        parts.append(f"# {module.title} {{.titre-module}}\n")
    if module.objectives:
        items = "\n".join(f"- {o}" for o in module.objectives)
        parts.append(f"## Objectifs {{.objectifs-module}}\n\n{items}\n")
    parts.append(f"{{{{< include /modules/{module.id}/slides.qmd >}}}}\n")
    return "\n".join(parts)


def _deck(front: str, blocks: list[str]) -> str:
    return front + "\n" + "{{< include /commun/_macros.qmd >}}\n\n" + "\n".join(blocks)


def _module_decks(root: Path, out: Path, module: Module) -> list[Path]:
    folder = out / "modules" / module.slug
    # Deck isolé : aucun module ne précède, tous les rappels sont affichés.
    missing = list(module.prerequisites)
    fingerprint = _fingerprint(root, [f"modules/{module.id}/slides.qmd"])
    written = []
    for name, options in MODULE_DECKS.items():
        front = _front_matter(
            title=module.title,
            subtitle=options_label(options).capitalize(),
            footer=module.title,
            ecoelec={"vue": "version", "empreinte": fingerprint},
        )
        body = _module_body(module, options, missing, section_title=False)
        written.append(_write(folder / f"{name}.qmd", _deck(front, [body])))
    front = _front_matter(
        title=module.title,
        subtitle="Vue auteur",
        footer=f"{module.title} — vue auteur",
        ecoelec={"vue": "auteur", "empreinte": fingerprint},
    )
    body = _module_body(module, OPTIONS, missing, section_title=False)
    written.append(_write(folder / "auteur.qmd", _deck(front, [body])))
    return written


def _agenda(session: Session) -> str:
    items = "\n".join(f"- {e.module.title}" for e in session.entries)
    return f"## Au programme\n\n{items}\n"


def _session_deck(root: Path, track: Track, session: Session) -> str:
    sources = [f"modules/{e.module.id}/slides.qmd" for e in session.entries]
    sources += [path for path in (session.introduction, session.conclusion) if path]
    front = _front_matter(
        title=session.title,
        subtitle=f"{track.title} — séance {session.number}",
        footer=f"{track.title} — séance {session.number}",
        ecoelec={"vue": "version", "empreinte": _fingerprint(root, sources)},
    )
    blocks = []
    if session.introduction:
        blocks.append(f"{{{{< include /{session.introduction} >}}}}\n")
    if len(session.entries) > 1:
        blocks.append(_agenda(session))
    for entry in session.entries:
        blocks.append(_module_body(entry.module, entry.options, entry.missing, section_title=True))
    if session.conclusion:
        blocks.append(f"{{{{< include /{session.conclusion} >}}}}\n")
    return _deck(front, blocks)


def _track_decks(root: Path, out: Path, track: Track) -> list[Path]:
    folder = out / "parcours" / track.name
    written = [
        _write(folder / f"seance-{s.number:02d}.qmd", _session_deck(root, track, s))
        for s in track.sessions
    ]
    written.append(_write(folder / "index.qmd", _track_index(track)))
    return written


def _minutes(value: int | None) -> str:
    return "à estimer" if value is None else f"{value} min"


def _entry_line(entry: Entry, chapter_prefix: str) -> str:
    line = (
        f"[{entry.module.title}]({chapter_prefix}modules/{entry.module.id}/poly.html) — "
        f"{options_label(entry.options)} ({_minutes(entry.duration)})"
    )
    if entry.missing:
        line += f" — rappels : {', '.join(entry.missing)}"
    return f"- {line}"


def _track_index(track: Track) -> str:
    # Depuis _rendu/slides/decks/parcours/<nom>/ jusqu'au poly, rendu dans _rendu/poly/
    chapter_prefix = "../../../../poly/"
    total = sum(s.duration for s in track.sessions)
    lines = [
        _front_matter(title=track.title, subtitle=f"Parcours {track.name}", format="html").rstrip(),
        "",
        f"Modules : {options_label(track.options)}. Durée totale : {total} min.",
        "",
    ]
    for session in track.sessions:
        lines += [
            f"## Séance {session.number} : {session.title}",
            "",
            (
                f"[Deck](seance-{session.number:02d}.html) — {session.duration} min prévues, "
                f"modules : {_minutes(session.declared)}."
            ),
            "",
            "Chapitres du poly à lire :",
            "",
            *[_entry_line(e, chapter_prefix) for e in session.entries],
            "",
        ]
    return "\n".join(lines)


def _site_index(modules: dict[str, Module], tracks: list[Track]) -> str:
    lines = [_front_matter(title="Slides du cours", format="html").rstrip(), "", "## Parcours", ""]
    lines += [
        f"- [{t.title}](parcours/{t.name}/index.html) — {len(t.sessions)} séance(s)" for t in tracks
    ]
    lines += ["", "## Modules", ""]
    for module in modules.values():
        versions = " · ".join(
            f"[{options_label(options)}](modules/{module.slug}/{name}.html)"
            for name, options in MODULE_DECKS.items()
        )
        lines.append(
            f"- **{module.title}** ({module.id}) : {versions} · [vue auteur](modules/{module.slug}/auteur.html)"
        )
    return "\n".join(lines) + "\n"
