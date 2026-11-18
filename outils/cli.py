"""Commande `ecoelec`.

uv run ecoelec verifier             vérifie modules, parcours et liste des chapitres du poly
uv run ecoelec generer              vérifie puis génère les decks dans decks/
uv run ecoelec nouveau-module ID --titre "Titre"   crée un module en ébauche
uv run ecoelec controler poly.log slides.log      contrôle les journaux et le rendu HTML
uv run ecoelec pdf                  exporte en PDF les decks autonomes (decktape + Chrome)
uv run ecoelec site                 racine du site publié : accueil et adresses des parcours
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from outils import options_label
from outils.catalog import load_modules
from outils.controls import check_images, check_logs
from outils.decks import OUTPUT, generate
from outils.report import Report
from outils.site import write_site
from outils.tracks import Track, load_tracks

MODULE_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def find_root(start: Path) -> Path:
    for folder in [start, *start.parents]:
        if (folder / "_quarto.yml").exists() and (folder / "modules").is_dir():
            return folder
    sys.exit("Racine du projet introuvable (dossier contenant _quarto.yml et modules/).")


def check(root: Path) -> tuple[Report, dict, list[Track]]:
    report = Report()
    modules = load_modules(root, report)
    tracks = load_tracks(root, modules, report)
    _check_book(root, modules, report)
    return report, modules, tracks


def _check_book(root: Path, modules: dict, report: Report) -> None:
    """Le poly est complet : chaque module y a son chapitre, chaque chapitre existe."""
    config = yaml.safe_load((root / "_quarto-poly.yml").read_text(encoding="utf-8"))
    chapters = []
    for item in config.get("book", {}).get("chapters", []):
        if isinstance(item, str):
            chapters.append(item)
        elif isinstance(item, dict):
            chapters += item.get("chapters", [])
    for chapter in chapters:
        if not (root / chapter).exists():
            report.error("_quarto-poly.yml", f"chapitre introuvable : {chapter}")
    for module in modules.values():
        expected = f"modules/{module.id}/poly.qmd"
        if not module.is_example and expected not in chapters:
            report.error("_quarto-poly.yml", f"chapitre absent du poly : {expected}")


def _summary(tracks: list[Track]) -> None:
    for track in tracks:
        print(f"\n{track.name} — {track.title} ({options_label(track.options)})")
        for s in track.sessions:
            declared = "à estimer" if s.declared is None else f"{s.declared} min"
            print(f"  séance {s.number:>2} ({s.duration} min, modules : {declared}) : {s.title}")
            for e in s.entries:
                minutes = "?" if e.duration is None else e.duration
                recall = f"  [rappels : {', '.join(e.missing)}]" if e.missing else ""
                label = options_label(e.options)
                print(f"      {e.module.id:<22} {label:<40} {minutes:>4}{recall}")


def cmd_check(args) -> int:
    report, _, tracks = check(args.root)
    _summary(tracks)
    print()
    report.print(verbose=args.verbose)
    return 0 if report.ok else 1


def cmd_generate(args) -> int:
    report, modules, tracks = check(args.root)
    report.print(verbose=args.verbose)
    if not report.ok:
        print("\nGénération annulée : corriger les erreurs d'abord.")
        return 1
    written = generate(args.root, modules, tracks)
    print(f"\n{len(written)} fichiers générés dans {OUTPUT}/")
    return 0


def cmd_site(args) -> int:
    report, _, tracks = check(args.root)
    if not report.ok:
        report.print()
        return 1
    rendu = args.root / args.rendu
    missing = [d for d in ("poly", "slides", "outils") if not (rendu / d).is_dir()]
    if missing:
        print(f"Rendu incomplet dans {args.rendu}/ : {', '.join(missing)} manquant(s)")
        return 1
    written = write_site(rendu, tracks)
    print(f"{len(written)} fichiers écrits à la racine de {args.rendu}/")
    return 0


MODULE_YML = """\
titre: {title}
prerequis: []
objectifs: []
duree: null                          # minutes de la base
tp: []
"""

POLY_QMD = """\
# {title} {{#sec-{id}}}

{{{{< include /commun/_macros.qmd >}}}}

::: {{.callout-note}}
Chapitre à rédiger.
:::
"""

SLIDES_QMD = """\
## À rédiger

Module en ébauche.
"""


def cmd_new_module(args) -> int:
    if not MODULE_ID.match(args.id):
        print(f"Identifiant invalide : {args.id} (minuscules, chiffres et tirets)")
        return 1
    folder = args.root / "modules" / args.id
    if folder.exists():
        print(f"{folder} existe déjà")
        return 1
    folder.mkdir(parents=True)
    title = args.titre or args.id
    (folder / "module.yml").write_text(
        MODULE_YML.format(title=json.dumps(title, ensure_ascii=False)), encoding="utf-8"
    )
    (folder / "poly.qmd").write_text(POLY_QMD.format(title=title, id=args.id), encoding="utf-8")
    (folder / "slides.qmd").write_text(SLIDES_QMD, encoding="utf-8")
    print(f"Module créé : modules/{args.id}/")
    print(f"À faire : ajouter modules/{args.id}/poly.qmd aux chapitres de _quarto-poly.yml.")
    return 0


def cmd_control(args) -> int:
    problems = check_logs(args.journaux) + check_images(args.root / args.rendu)
    for problem in problems:
        print(f"✗ {problem}")
    print(f"{len(problems)} problème(s)")
    return 1 if problems else 0


CHROME_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")


def cmd_pdf(args) -> int:
    chrome = args.chrome or os.environ.get("CHROME_PATH")
    chrome = chrome or next((p for p in map(shutil.which, CHROME_NAMES) if p), None)
    if not chrome:
        print("Chrome ou Chromium introuvable : préciser --chrome")
        return 1
    decks = sorted((args.root / args.dossier).rglob("seance-*.html"))
    if not decks:
        print(f"Aucun deck dans {args.dossier} : rendre d'abord les decks autonomes")
        return 1
    env = {**os.environ, "PUPPETEER_SKIP_DOWNLOAD": "true"}
    for deck in decks:
        target = deck.with_suffix(".pdf")
        command = [
            "npx", "--yes", "decktape@3", "reveal",
            "--chrome-path", chrome, "--chrome-arg=--no-sandbox", "--size", "1280x720",
            deck.resolve().as_uri(), str(target),
        ]  # fmt: skip
        print(f"→ {target.relative_to(args.root)}")
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(result.stdout[-2000:], result.stderr[-2000:])
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ecoelec", description="Outillage du cours d'économie de l'électricité"
    )
    parser.add_argument("--racine", dest="root", type=Path, default=None, help="racine du projet")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("verifier", help="vérifier modules, parcours et chapitres du poly")
    p.add_argument("-v", "--verbose", action="store_true", help="afficher aussi les infos")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("generer", help="vérifier puis générer les decks dans decks/")
    p.add_argument("-v", "--verbose", action="store_true", help="afficher aussi les infos")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("nouveau-module", help="créer un module en ébauche")
    p.add_argument("id", help="identifiant du module (ex. court-terme)")
    p.add_argument("--titre", help="titre du module")
    p.set_defaults(func=cmd_new_module)

    p = sub.add_parser(
        "controler", help="contrôler les journaux de rendu et les images du rendu HTML"
    )
    p.add_argument("journaux", nargs="*", type=Path, help="journaux de quarto render")
    p.add_argument("--rendu", default="_rendu", help="dossier du rendu (défaut : _rendu)")
    p.set_defaults(func=cmd_control)

    p = sub.add_parser("pdf", help="exporter en PDF les decks autonomes (decktape)")
    p.add_argument("--dossier", default="_rendu/autonome", help="dossier des decks autonomes")
    p.add_argument("--chrome", help="chemin de Chrome ou Chromium")
    p.set_defaults(func=cmd_pdf)

    p = sub.add_parser("site", help="écrire la racine du site publié (accueil, parcours)")
    p.add_argument("--rendu", default="_rendu", help="dossier du rendu (défaut : _rendu)")
    p.set_defaults(func=cmd_site)

    args = parser.parse_args(argv)
    args.root = (args.root or find_root(Path.cwd())).resolve()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
