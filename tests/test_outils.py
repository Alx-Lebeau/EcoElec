"""Tests de la lecture des modules et parcours, et de la génération des decks."""

import json
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
    assert [(e.module.id, e.options) for e in session.entries] == [
        ("base", ()),
        ("suite", ("approfondissement", "formel")),
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


def test_options_and_supplements(project: Path):
    write(
        project / "modules/suite/module.yml",
        module_yml("suite", ["base"], minutes=20) + "supplements: {formel: 5}\n",
    )
    write(
        project / "modules/suite/slides.qmd",
        "## Rappel {.rappel}\n\n## Suite\n\n::: {.formel}\nMaths.\n:::\n\n## Plus {.approfondissement}\n",
    )
    write(
        project / "parcours/court.yml",
        """\
        titre: Parcours court
        options: [approfondissement, formel]
        seances:
          - titre: Séance unique
            duree: 60
            modules:
              - base
              - suite: {sans: approfondissement}
        """,
    )
    report, modules, tracks = check(project)
    assert report.ok, [str(m) for m in report.messages]
    suite = modules["suite"]
    assert suite.duration() == 20 and suite.duration(["formel"]) == 25
    # Slides marquées .approfondissement sans supplément déclaré : durée à estimer
    assert suite.duration(["approfondissement"]) is None
    assert any("suppléments à estimer" in t for t in messages(report, "alerte"))
    base, entry = tracks[0].sessions[0].entries
    assert base.options == ("approfondissement", "formel")
    assert entry.options == ("formel",) and entry.duration == 25


def test_invalid_option_and_removed_mark(project: Path):
    write(project / "modules/base/slides.qmd", "## Base\n\n::: {.intuitif}\nLiaison.\n:::\n")
    write(
        project / "parcours/court.yml",
        "titre: X\nseances:\n  - titre: S\n    duree: 60\n    modules:\n      - base: {avec: complet}\n",
    )
    report, _, _ = check(project)
    errors = messages(report, "erreur")
    assert any("marque .intuitif supprimée" in t for t in errors)
    assert any("base, avec" in t for t in errors)


def test_missing_prerequisite(project: Path):
    write(
        project / "parcours/court.yml",
        """\
        titre: Parcours court
        options: [formel]
        seances:
          - titre: Séance unique
            duree: 60
            modules:
              - suite
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
        "titre: X\nseances:\n  - titre: S\n    duree: 30\n    modules:\n      - absent\n",
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
    for name in ["base", "integral", "auteur"]:
        assert (out / f"modules/suite/{name}.qmd").exists()
    deck = (out / "parcours/court/seance-01.qmd").read_text(encoding="utf-8")
    assert 'module="suite" options="approfondissement formel" manquants=""' in deck
    assert "{{< include /modules/suite/slides.qmd >}}" in deck
    assert "## Au programme" in deck
    # Deck isolé d'un module : tous ses prérequis sont manquants
    alone = (out / "modules/suite/base.qmd").read_text(encoding="utf-8")
    assert 'options="" manquants="base"' in alone
    assert not (out / "index.qmd").exists()  # accueil : application React (accueil/)
    assert (out / "catalogue.json").exists()


def test_fingerprint_follows_included_files(project: Path):
    _, modules, tracks = check(project)
    generate(project, modules, tracks)
    deck = project / OUTPUT / "parcours/court/seance-01.qmd"
    before = deck.read_text(encoding="utf-8")
    write(project / "modules/suite/slides.qmd", "## Rappel {.rappel}\n\nModifié.\n")
    generate(project, modules, tracks)
    assert deck.read_text(encoding="utf-8") != before


def test_catalogue(project: Path):
    write(project / "modules/suite/outil.qmd", "---\ntitle: Outil\n---\n")
    write(project / "modules/_exemple/module.yml", module_yml("exemple", []))
    write(project / "modules/_exemple/poly.qmd", "# exemple\n")
    write(project / "modules/_exemple/slides.qmd", "## Exemple\n")
    _, modules, tracks = check(project)
    assert modules["suite"].has_tool and not modules["base"].has_tool
    generate(project, modules, tracks)
    data = json.loads((project / OUTPUT / "catalogue.json").read_text(encoding="utf-8"))
    # Ordre du poly, sans le module d'exemple
    assert [m["id"] for m in data["modules"]] == ["base", "suite"]
    base, suite = data["modules"]
    assert base["outil"] is None
    assert suite["outil"] == "outils/modules/suite/outil.html"
    assert suite["chapitre"] == "poly/modules/suite/poly.html"
    assert suite["slides"]["integral"] == "slides/decks/modules/suite/integral.html"
    assert suite["utilisations"] == [{"parcours": "court", "seance": 1}]
    (track,) = data["parcours"]
    assert (track["nom"], track["duree"]) == ("court", 60)
    (session,) = track["seances"]
    assert session["deck"] == "slides/decks/parcours/court/seance-01.html"
    assert session["autonome"] == "autonome/decks/parcours/court/seance-01.html"
    assert session["modules"][1] == {
        "id": "suite",
        "options": ["approfondissement", "formel"],
        "duree": 30,
        "rappels": [],
    }


def test_site_root(project: Path):
    from outils.site import write_site

    _, _, tracks = check(project)
    rendu = project / "_rendu"
    write_site(rendu, tracks)
    short = (rendu / "parcours/court/index.html").read_text(encoding="utf-8")
    assert 'url=../../#/parcours/court"' in short
    assert (rendu / ".nojekyll").exists()
    assert not (rendu / "index.html").exists()  # construit par `npm run build`
