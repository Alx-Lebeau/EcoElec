"""Tests des filtres Lua, avec le pandoc fourni par Quarto (ignorés si Quarto est absent)."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FILTERS = ROOT / "commun" / "filtres"

pytestmark = pytest.mark.skipif(shutil.which("quarto") is None, reason="Quarto absent")

DECK = """\
---
ecoelec:
  vue: {vue}
---

::: {{.ecoelec-module module="m" profondeur="{depth}" formalisme="{formalism}" manquants="{missing}"}}
:::

## Commune

Texte commun[ et liaison]{{.intuitif}}.

::: {{.formel}}
Bloc formel.
:::

::: {{.rappel module="autre"}}
Rappel autre.
:::

::: {{.rappel module="systeme"}}
Rappel systeme.
:::

## Démonstration {{.formel}}

Contenu de la démonstration.

## Approfondie {{.approfondissement}}

Contenu approfondi.

## Finale

Fin.
"""


def render(filter_name: str, markdown: str, to: str = "markdown") -> str:
    result = subprocess.run(
        [
            "quarto",
            "pandoc",
            "-f",
            "markdown",
            "-t",
            to,
            "--lua-filter",
            str(FILTERS / filter_name),
        ],
        input=markdown,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def deck(vue="version", depth="essentiel", formalism="intuitif", missing="") -> str:
    md = DECK.format(vue=vue, depth=depth, formalism=formalism, missing=missing)
    return render("marques.lua", md)


def test_essential_intuitive():
    out = deck(depth="essentiel", formalism="intuitif", missing="systeme")
    assert "et liaison" in out
    assert "Bloc formel" not in out
    assert "Démonstration" not in out and "Contenu de la démonstration" not in out
    assert "Approfondie" not in out
    assert "Rappel systeme" in out and "Rappel autre" not in out
    assert "Finale" in out


def test_complete_formal():
    out = deck(depth="complet", formalism="formel")
    assert "et liaison" not in out
    assert "Bloc formel" in out and "Contenu de la démonstration" in out
    assert "Contenu approfondi" in out
    assert "Rappel" not in out


def test_author_view_keeps_everything_with_visible_marks():
    out = deck(vue="auteur")
    for text in [
        "et liaison",
        "Bloc formel",
        "Rappel autre",
        "Contenu de la démonstration",
        "Contenu approfondi",
    ]:
        assert text in out
    for mark in ["marque-intuitif", "marque-formel", "marque-rappel", "marque-approfondissement"]:
        assert mark in out


LIST = """\
::: {{.ecoelec-module module="m" profondeur="{depth}" formalisme="intuitif" manquants=""}}
:::

## Liste

- premier point
- [point approfondi]{{.approfondissement}}
- dernier point

Paragraphe[ approfondi]{{.approfondissement}}.

- [seul point approfondi]{{.approfondissement}}
"""


def test_no_empty_bullet_when_item_hidden():
    out = render("marques.lua", LIST.format(depth="essentiel"))
    assert "point approfondi" not in out
    assert "premier point" in out and "dernier point" in out
    lines = [line.strip() for line in out.splitlines()]
    assert "-" not in lines  # aucune puce vide
    assert out.count("- ") == 2  # la liste entièrement masquée disparaît
    assert "Paragraphe." in out
    full = render("marques.lua", LIST.format(depth="complet"))
    assert "point approfondi" in full and full.count("- ") == 4


def test_formalisation_box():
    md = '::: {.formalisation titre="Dualité"}\nDéveloppement.\n:::\n'
    out = render("formalisation.lua", md, to="html")
    assert "callout-note" in out and "Formalisation\u00a0: Dualité" in out
    hidden = render(
        "formalisation.lua", "---\necoelec:\n  formalisation: false\n---\n\n" + md, to="html"
    )
    assert "Développement" not in hidden


def test_french_typography():
    out = render("typographie.lua", "Durée : 90 min ; « prix » ? `a : b`\n", to="native")
    assert 'Str "\\160"' in out  # insécable avant les deux-points
    assert 'Str "\\8239"' in out  # fine insécable
    assert '"a : b"' in out  # code intact


PARTIES = """\
::: {.ecoelec-module module="a"}
:::

## Un {partie="Physique"}

## Deux

## Trois {partie="Organisation"}

::: {.ecoelec-module module="b"}
:::

## Quatre
"""


def test_parties_propagees_et_comptees():
    out = render("parties.lua", PARTIES, to="native")
    blocks = out.split("Header")
    assert '"data-partie" , "Physique"' in blocks[1] and "--partie: 1; --parties: 2" in blocks[1]
    assert '"data-partie" , "Physique"' in blocks[2]  # la partie se prolonge
    assert "--partie: 2; --parties: 2" in blocks[3]
    assert "data-partie" not in blocks[4]  # nouveau module : pas de partie
    assert '( "partie"' not in out  # l'attribut d'origine est retiré
