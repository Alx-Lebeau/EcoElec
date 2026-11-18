"""Site publié (GitHub Pages) : catalogue de l'accueil et adresses courtes des parcours.

    decks/catalogue.json               écrit par `ecoelec generer`, lu par l'accueil React
                                       (accueil/, construit dans _rendu/ par `npm run build`)
    _rendu/parcours/<nom>/index.html   adresse courte d'un parcours, à donner au public
    _rendu/.nojekyll                   GitHub Pages sert les fichiers tels quels

Le poly (_rendu/poly/), les slides (_rendu/slides/), les decks autonomes
(_rendu/autonome/) et les outils (_rendu/outils/) sont rendus par Quarto. Le catalogue
donne leurs chemins relativement à la racine _rendu/.
"""

import json
from html import escape
from pathlib import Path

import yaml

from outils import OPTION_LABELS, OPTIONS
from outils.catalog import Module, book_chapters
from outils.tracks import Track

CATALOGUE = "catalogue.json"
POLY_PDF = "poly/economie-electricite.pdf"


def _module_entry(module: Module, tracks: list[Track]) -> dict:
    decks = f"slides/decks/modules/{module.slug}"
    uses = [
        {"parcours": t.name, "seance": s.number}
        for t in tracks
        for s in t.sessions
        if any(e.module.id == module.id for e in s.entries)
    ]
    return {
        "id": module.id,
        "titre": module.title,
        "prerequis": module.prerequisites,
        "objectifs": module.objectives,
        "duree": module.base_duration,
        "supplements": {o: module.extras.get(o, 0) for o in OPTIONS},
        "tp": module.tp,
        "chapitre": f"poly/modules/{module.id}/poly.html",
        "outil": f"outils/modules/{module.id}/outil.html" if module.has_tool else None,
        "slides": {name: f"{decks}/{name}.html" for name in ("base", "integral", "auteur")},
        "utilisations": uses,
    }


def _track_entry(track: Track) -> dict:
    sessions = []
    for s in track.sessions:
        deck = f"decks/parcours/{track.name}/seance-{s.number:02d}"
        sessions.append(
            {
                "numero": s.number,
                "titre": s.title,
                "duree": s.duration,
                "duree_modules": s.declared,
                "deck": f"slides/{deck}.html",
                "autonome": f"autonome/{deck}.html",
                "pdf": f"autonome/{deck}.pdf",
                "modules": [
                    {
                        "id": e.module.id,
                        "options": list(e.options),
                        "duree": e.duration,
                        "rappels": e.missing,
                    }
                    for e in s.entries
                ],
            }
        )
    return {
        "nom": track.name,
        "titre": track.title,
        "options": list(track.options),
        "duree": sum(s.duration for s in track.sessions),
        "seances": sessions,
    }


def catalogue(root: Path, modules: dict[str, Module], tracks: list[Track]) -> dict:
    """Contenu du site : modules dans l'ordre du poly (sans le module d'exemple), parcours."""
    config = yaml.safe_load((root / "_quarto-poly.yml").read_text(encoding="utf-8")) or {}
    book = config.get("book", {})
    order = {c: i for i, c in enumerate(book_chapters(root))}
    public = [m for m in modules.values() if not m.is_example]
    public.sort(key=lambda m: order.get(f"modules/{m.id}/poly.qmd", len(order)))
    return {
        "titre": book.get("title", "Économie de l'électricité"),
        "sous_titre": book.get("subtitle", ""),
        "auteur": book.get("author", ""),
        "options": OPTION_LABELS,
        "poly": {"html": "poly/index.html", "pdf": POLY_PDF},
        "modules": [_module_entry(m, tracks) for m in public],
        "parcours": [_track_entry(t) for t in tracks],
    }


def write_catalogue(path: Path, root: Path, modules: dict[str, Module], tracks) -> Path:
    data = catalogue(root, modules, tracks)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def _redirect(target: str, title: str) -> str:
    target, title = escape(target, quote=True), escape(title)
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{target}">
</head>
<body><p><a href="{target}">{title}</a></p></body>
</html>
"""


def write_site(rendu: Path, tracks: list[Track]) -> list[Path]:
    """Écrit les adresses courtes des parcours dans `rendu` et renvoie les fichiers écrits.

    L'accueil (`rendu/index.html`) est construit à part par `npm run build` (accueil/).
    """
    written = []

    def write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)

    for track in tracks:
        target = f"../../#/parcours/{track.name}"
        write(rendu / "parcours" / track.name / "index.html", _redirect(target, track.title))
    write(rendu / ".nojekyll", "")
    return written
