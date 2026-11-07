"""Lecture et vérification des modules (modules/<id>/module.yml)."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from outils import DEPTHS, FORMALISMS
from outils.report import Report

MODULE_KEYS = {"titre", "prerequis", "objectifs", "durees", "tp"}
# Repère une marque .rappel dans les attributs d'un bloc, d'une slide ou d'un passage.
RECALL_PATTERN = re.compile(r"\{[^}]*\.rappel\b")


@dataclass
class Module:
    id: str
    path: Path
    title: str
    prerequisites: list[str] = field(default_factory=list)
    objectives: list[str] = field(default_factory=list)
    # durations[(profondeur, formalisme)] = minutes, ou None si non estimée
    durations: dict[tuple[str, str], int | None] = field(default_factory=dict)
    tp: list[str] = field(default_factory=list)
    has_recall: bool = False

    @property
    def is_example(self) -> bool:
        """Les dossiers préfixés par « _ » (modèle, exemple) ne vont ni dans le poly ni dans les parcours."""
        return self.id.startswith("_")

    @property
    def slug(self) -> str:
        """Nom des fichiers générés : Quarto ignore les chemins commençant par « _ »."""
        return self.id.lstrip("_")

    def duration(self, depth: str, formalism: str) -> int | None:
        return self.durations.get((depth, formalism))


def module_dirs(root: Path) -> list[Path]:
    return sorted(p.parent for p in (root / "modules").glob("*/module.yml"))


def load_modules(root: Path, report: Report) -> dict[str, Module]:
    modules: dict[str, Module] = {}
    for folder in module_dirs(root):
        module = _load_module(folder, root, report)
        if module:
            modules[module.id] = module
    _check_prerequisites(modules, report)
    return modules


def _load_module(folder: Path, root: Path, report: Report) -> Module | None:
    where = str(folder.relative_to(root))
    try:
        data = yaml.safe_load((folder / "module.yml").read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        report.error(where, f"module.yml illisible ({exc})")
        return None

    unknown = set(data) - MODULE_KEYS
    if unknown:
        report.warning(where, f"clés inconnues dans module.yml : {', '.join(sorted(unknown))}")

    title = data.get("titre")
    if not isinstance(title, str) or not title.strip():
        report.error(where, "titre manquant")
        return None

    for name in ("poly.qmd", "slides.qmd"):
        if not (folder / name).exists():
            report.error(where, f"{name} manquant")

    module = Module(
        id=folder.name,
        path=folder,
        title=title.strip(),
        prerequisites=_as_list(data.get("prerequis"), where, "prerequis", report),
        objectives=_as_list(data.get("objectifs"), where, "objectifs", report),
        durations=_read_durations(data.get("durees"), where, report),
        tp=_as_list(data.get("tp"), where, "tp", report),
    )
    slides = folder / "slides.qmd"
    module.has_recall = slides.exists() and bool(
        RECALL_PATTERN.search(slides.read_text(encoding="utf-8"))
    )

    todo = []
    if not module.objectives:
        todo.append("objectifs à rédiger")
    if any(v is None for v in module.durations.values()):
        todo.append("durées à estimer")
    if todo and not module.is_example:
        report.warning(where, " ; ".join(todo))
    for tp in module.tp:
        if not (folder / "tp" / f"{tp}.ipynb").exists():
            report.warning(where, f"TP « {tp} » introuvable (tp/{tp}.ipynb)")
    return module


def _as_list(value, where: str, key: str, report: Report) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return value
    report.error(where, f"« {key} » doit être une liste de textes")
    return []


def _read_durations(value, where: str, report: Report) -> dict[tuple[str, str], int | None]:
    durations: dict[tuple[str, str], int | None] = {}
    if not isinstance(value, dict):
        report.error(where, "« durees » manquant ou mal formé (profondeur → formalisme → minutes)")
        return {(d, f): None for d in DEPTHS for f in FORMALISMS}
    for depth in DEPTHS:
        row = value.get(depth)
        if not isinstance(row, dict):
            report.error(where, f"durées : profondeur « {depth} » manquante")
            row = {}
        for formalism in FORMALISMS:
            minutes = row.get(formalism)
            if minutes is not None and (not isinstance(minutes, int) or minutes <= 0):
                report.error(where, f"durée {depth}/{formalism} invalide : {minutes!r}")
                minutes = None
            durations[(depth, formalism)] = minutes
    return durations


def _check_prerequisites(modules: dict[str, Module], report: Report) -> None:
    for module in modules.values():
        where = f"modules/{module.id}"
        for prereq in module.prerequisites:
            if prereq not in modules:
                report.error(where, f"prérequis inconnu : {prereq}")
            elif modules[prereq].is_example:
                report.error(
                    where, f"prérequis {prereq} : un module d'exemple ne peut pas être prérequis"
                )
    # Cycles
    state: dict[str, str] = {}

    def visit(mid: str, chain: list[str]) -> None:
        if state.get(mid) == "fait" or mid not in modules:
            return
        if state.get(mid) == "en cours":
            cycle = " → ".join([*chain[chain.index(mid) :], mid])
            report.error(f"modules/{mid}", f"prérequis circulaires : {cycle}")
            return
        state[mid] = "en cours"
        for prereq in modules[mid].prerequisites:
            visit(prereq, [*chain, mid])
        state[mid] = "fait"

    for mid in modules:
        visit(mid, [])
