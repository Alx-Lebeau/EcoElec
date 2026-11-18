"""Lecture et vérification des modules (modules/<id>/module.yml)."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from outils import OPTIONS
from outils.report import Report

MODULE_KEYS = {"titre", "prerequis", "objectifs", "duree", "supplements", "tp"}
# Marques retirées : les signaler plutôt que de les laisser sans effet.
REMOVED_MARKS = {
    "intuitif": "le contenu non marqué doit tenir seul, sans phrase de liaison réservée"
}


def _mark_pattern(mark: str) -> re.Pattern:
    """Repère une marque dans les attributs d'un bloc, d'une slide ou d'un passage."""
    return re.compile(r"\{[^}]*\." + mark + r"\b")


@dataclass
class Module:
    id: str
    path: Path
    title: str
    prerequisites: list[str] = field(default_factory=list)
    objectives: list[str] = field(default_factory=list)
    # Durée de la base en minutes, ou None si non estimée
    base_duration: int | None = None
    # Minutes ajoutées par chaque option, ou None si non estimées
    extras: dict[str, int | None] = field(default_factory=dict)
    tp: list[str] = field(default_factory=list)
    has_recall: bool = False

    @property
    def is_example(self) -> bool:
        """Les dossiers préfixés par « _ » (modèle, exemple) ne vont ni dans le poly ni dans les parcours."""
        return self.id.startswith("_")

    @property
    def has_tool(self) -> bool:
        """Outil interactif (page OJS `outil.qmd`, rendue par le profil `outils`)."""
        return (self.path / "outil.qmd").exists()

    @property
    def slug(self) -> str:
        """Nom des fichiers générés : Quarto ignore les chemins commençant par « _ »."""
        return self.id.lstrip("_")

    def duration(self, options=()) -> int | None:
        """Durée de la base et des options choisies, ou None si l'une n'est pas estimée."""
        values = [self.base_duration, *(self.extras.get(o, 0) for o in options)]
        return None if any(v is None for v in values) else sum(values)


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
        tp=_as_list(data.get("tp"), where, "tp", report),
    )
    slides = folder / "slides.qmd"
    text = slides.read_text(encoding="utf-8") if slides.exists() else ""
    module.has_recall = bool(_mark_pattern("rappel").search(text))
    for mark, reason in REMOVED_MARKS.items():
        if _mark_pattern(mark).search(text):
            report.error(where, f"marque .{mark} supprimée ({reason})")
    module.base_duration = _minutes(data.get("duree"), "duree", where, report)
    module.extras = _read_extras(data.get("supplements"), text, where, report)

    todo = []
    if not module.objectives:
        todo.append("objectifs à rédiger")
    pending = [o for o in OPTIONS if module.extras[o] is None]
    if module.base_duration is None:
        todo.append("durée à estimer")
    elif pending:
        todo.append(f"suppléments à estimer ({', '.join(pending)})")
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


def _minutes(value, key: str, where: str, report: Report) -> int | None:
    if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
        report.error(where, f"« {key} » invalide : {value!r} (minutes attendues)")
        return None
    return value


def _read_extras(value, slides: str, where: str, report: Report) -> dict[str, int | None]:
    """Minutes ajoutées par option. Sans valeur : 0 si les slides n'ont pas la marque, sinon à estimer."""
    if value is None:
        value = {}
    if not isinstance(value, dict):
        report.error(where, "« supplements » mal formé (option → minutes)")
        value = {}
    unknown = set(value) - set(OPTIONS)
    if unknown:
        report.error(
            where,
            f"suppléments inconnus : {', '.join(sorted(map(str, unknown)))} "
            f"({' ou '.join(OPTIONS)} attendu)",
        )
    extras: dict[str, int | None] = {}
    for option in OPTIONS:
        minutes = _minutes(value.get(option), f"supplements.{option}", where, report)
        if minutes is None and not _mark_pattern(option).search(slides):
            minutes = 0
        extras[option] = minutes
    return extras


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
