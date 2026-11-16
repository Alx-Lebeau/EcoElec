"""Projet minimal construit dans un dossier temporaire pour tester l'outillage."""

import textwrap
from pathlib import Path

import pytest


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


def module_yml(title: str, prereqs: list[str], minutes: int | None = 30) -> str:
    m = "null" if minutes is None else minutes
    return textwrap.dedent(f"""\
        titre: "{title}"
        prerequis: [{", ".join(prereqs)}]
        objectifs: [Comprendre {title}]
        duree: {m}
        tp: []
        """)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    write(tmp_path / "_quarto.yml", "project:\n  output-dir: _rendu\n")
    write(
        tmp_path / "_quarto-poly.yml",
        """\
        book:
          chapters:
            - index.qmd
            - modules/base/poly.qmd
            - modules/suite/poly.qmd
        """,
    )
    write(tmp_path / "index.qmd", "# Accueil\n")
    write(tmp_path / "commun/_macros.qmd", "\\providecommand{\\R}{\\mathbb{R}}\n")
    for mid, prereqs, slides in [
        ("base", [], "## Base\n\nContenu.\n"),
        ("suite", ["base"], "## Rappel {.rappel}\n\nRappel.\n\n## Suite\n\nContenu.\n"),
    ]:
        write(tmp_path / f"modules/{mid}/module.yml", module_yml(mid, prereqs))
        write(tmp_path / f"modules/{mid}/poly.qmd", f"# {mid}\n")
        write(tmp_path / f"modules/{mid}/slides.qmd", slides)
    write(
        tmp_path / "parcours/court.yml",
        """\
        titre: Parcours court
        seances:
          - titre: Séance unique
            duree: 60
            modules:
              - base
              - suite: {avec: [approfondissement, formel]}
        """,
    )
    return tmp_path
