"""Chemins du projet.

Les cellules de code sont exécutées depuis le dossier du document rendu
(un chapitre du poly, un deck généré dans slides/…) : on ne s'appuie donc
jamais sur des chemins relatifs, mais sur la racine du projet.
"""

import os
from pathlib import Path


def _find_root() -> Path:
    # Quarto renseigne QUARTO_PROJECT_DIR pendant le rendu.
    env = os.environ.get("QUARTO_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    # Sinon (notebook, script) : premier dossier parent contenant _quarto.yml.
    for folder in [Path.cwd(), *Path.cwd().parents]:
        if (folder / "_quarto.yml").exists():
            return folder
    # À défaut : le dépôt qui contient ce paquet.
    return Path(__file__).resolve().parent.parent


ROOT = _find_root()
DATA_DIR = ROOT / "data"
