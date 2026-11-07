"""Tests de la lecture des modules et parcours, et de la génération des decks."""

from pathlib import Path

from conftest import module_yml, write

from outils.catalog import load_modules
from outils.cli import check
from outils.decks import OUTPUT, generate
from outils.report import Report
from outils.tracks import load_tracks


def messages(report: Report, level: str) -> list[str]:
    return [m.text for m in report.messages if m.level == level]


def test_valid_project(project: Path):
    report, modules, tracks = check(project)
    assert report.ok, [str(m) for m in report.messages]
    assert set(modules) == {"base", "suite"}
    assert modules["suite"].has_recall
    (session,) = tracks[0].sessions
    assert [(e.module.id, e.depth, e.formalism) for e in session.entries] == [
        ("base", "essentiel", "intuitif"),
        ("suite", "complet", "formel"),
    ]
    assert session.declared == 60
    # base précède suite : aucun prérequis manquant
    assert session.entries[1].missing == []


def test_duration_exceeded(project: Path):
    write(project / "modules/suite/module.yml", module_yml("suite", ["base"], minutes=45))
    report, _, _ = check(project)
    assert any("durée dépassée" in t for t in messages(report, "erreur"))


def test_unknown_duration_is_a_warning(project: Path):
    write(project / "modules/suite/module.yml", module_yml("suite", ["base"], minutes=None))
    report, _, _ = check(project)
    assert report.ok
    assert any("durée non vérifiable" in t for t in messages(report, "alerte"))


def test_missing_prerequisite(project: Path):
    write(
        project / "parcours/court.yml",
        """\
        titre: Parcours court
        formalisme: formel
        seances:
          - titre: Séance unique
            duree: 60
            modules:
              - suite: essentiel
        """,
    )
    report, _, tracks = check(project)
    assert tracks[0].sessions[0].entries[0].missing == ["base"]
    assert any("rappels inclus" in t for t in messages(report, "info"))
    # Sans slide de rappel : alerte
    write(project / "modules/suite/slides.qmd", "## Suite\n")
    report, _, _ = check(project)
    assert any("aucune slide de rappel" in t for t in messages(report, "alerte"))


def test_unknown_module_and_cycle(project: Path):
    write(project / "modules/base/module.yml", module_yml("base", ["suite"]))
    report = Report()
    modules = load_modules(project, report)
    assert any("circulaires" in t for t in messages(report, "erreur"))
    write(
        project / "parcours/court.yml",
        "titre: X\nformalisme: formel\nseances:\n  - titre: S\n    duree: 30\n    modules:\n      - absent: essentiel\n",
    )
    load_tracks(project, modules, report)
    assert any("module inconnu" in t for t in messages(report, "erreur"))


def test_book_must_list_every_module(project: Path):
    write(
        project / "_quarto-poly.yml",
        "book:\n  chapters:\n    - index.qmd\n    - modules/base/poly.qmd\n",
    )
    report, _, _ = check(project)
    assert any(
        "chapitre absent du poly : modules/suite/poly.qmd" in t for t in messages(report, "erreur")
    )


def test_generate(project: Path):
    _, modules, tracks = check(project)
    generate(project, modules, tracks)
    out = project / OUTPUT
    for name in [
        "essentiel-intuitif",
        "essentiel-formel",
        "complet-intuitif",
        "complet-formel",
        "auteur",
    ]:
        assert (out / f"modules/suite/{name}.qmd").exists()
    deck = (out / "parcours/court/seance-01.qmd").read_text(encoding="utf-8")
    assert 'module="suite" profondeur="complet" formalisme="formel" manquants=""' in deck
    assert "{{< include /modules/suite/slides.qmd >}}" in deck
    assert "## Au programme" in deck
    # Deck isolé d'un module : tous ses prérequis sont manquants
    alone = (out / "modules/suite/essentiel-intuitif.qmd").read_text(encoding="utf-8")
    assert 'manquants="base"' in alone
    assert (out / "parcours/court/index.qmd").exists()
    assert (out / "index.qmd").exists()


def test_fingerprint_follows_included_files(project: Path):
    _, modules, tracks = check(project)
    generate(project, modules, tracks)
    deck = project / OUTPUT / "parcours/court/seance-01.qmd"
    before = deck.read_text(encoding="utf-8")
    write(project / "modules/suite/slides.qmd", "## Rappel {.rappel}\n\nModifié.\n")
    generate(project, modules, tracks)
    assert deck.read_text(encoding="utf-8") != before
