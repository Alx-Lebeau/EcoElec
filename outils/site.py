"""Racine du site publié (GitHub Pages), au-dessus des trois rendus Quarto.

    _rendu/index.html                  redirige vers l'accueil (slides/decks/index.html)
    _rendu/parcours/<nom>/index.html   adresse courte d'un parcours, à donner au public
    _rendu/.nojekyll                   GitHub Pages sert les fichiers tels quels

Le poly (_rendu/poly/), les slides (_rendu/slides/) et les outils (_rendu/outils/)
sont rendus par leurs profils Quarto ; cette commande ne fait que les relier.
"""

from html import escape
from pathlib import Path

from outils.tracks import Track

HOME = "slides/decks/index.html"


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
    """Écrit la racine du site dans `rendu` et renvoie les fichiers écrits."""
    written = []

    def write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)

    write(rendu / "index.html", _redirect(HOME, "Économie de l'électricité"))
    for track in tracks:
        target = f"../../slides/decks/parcours/{track.name}/index.html"
        write(rendu / "parcours" / track.name / "index.html", _redirect(target, track.title))
    write(rendu / ".nojekyll", "")
    return written
